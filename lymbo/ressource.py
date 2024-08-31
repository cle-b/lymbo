import contextlib
from contextvars import ContextVar
import importlib
import inspect
from multiprocessing import Queue
from multiprocessing.managers import DictProxy
from multiprocessing.managers import SyncManager
import os
from pathlib import Path
import pickle
import queue
import sys
import time
from unittest.mock import patch

from lymbo.env import LYMBO_TEST_SCOPE_CLASS
from lymbo.env import LYMBO_TEST_SCOPE_FUNCTION
from lymbo.env import LYMBO_TEST_SCOPE_SESSION
from lymbo.env import LYMBO_TEST_SCOPE_MODULE

from lymbo.item import TestItem
from lymbo.item import TestPlan


shared_scopes: ContextVar = ContextVar("shared_scopes")
global_queue: Queue = Queue()


def set_scopes(scopes):
    shared_scopes.set(scopes)


@contextlib.contextmanager
def _cm_by_scope(scope_name, cm, *args, **kwargs):

    scopes = shared_scopes.get()
    global global_queue

    unique_cm_id = f"{cm.__module__}.{cm.__name__}.{args}.{kwargs}"

    scope = scopes[os.environ.get(scope_name)]
    with scope["lock"]:  # the lock is only for the request about the ressource creation

        if unique_cm_id not in scope["ressources"]:
            scope["ressources"][unique_cm_id] = None

            module_name = cm.__module__
            module = importlib.import_module(module_name)
            module_path = inspect.getfile(module)

            global_queue.put(
                {
                    "scope_id": os.environ.get(scope_name),
                    "ressource": {
                        "id": unique_cm_id,
                        "module_name": module_name,
                        "module_path": module_path,
                        "name": cm.__name__,
                        "args": args,
                        "kwargs": kwargs,
                    },
                }
            )

    while scope["ressources"][unique_cm_id] is None:
        time.sleep(0.2)  # TODO infinite loop risk

    ressource = pickle.loads(scope["ressources"][unique_cm_id])

    yield ressource


class LymboRessource:

    @staticmethod
    @contextlib.contextmanager
    def module(cm, *args, **kwargs):

        with _cm_by_scope(LYMBO_TEST_SCOPE_MODULE, cm, *args, **kwargs) as ressource:
            yield ressource

    @staticmethod
    @contextlib.contextmanager
    def cls(cm, *args, **kwargs):

        with _cm_by_scope(LYMBO_TEST_SCOPE_CLASS, cm, *args, **kwargs) as ressource:
            yield ressource

    @staticmethod
    @contextlib.contextmanager
    def function(cm, *args, **kwargs):

        with _cm_by_scope(LYMBO_TEST_SCOPE_FUNCTION, cm, *args, **kwargs) as ressource:
            yield ressource

    @staticmethod
    @contextlib.contextmanager
    def session(cm, *args, **kwargs):

        with _cm_by_scope(LYMBO_TEST_SCOPE_SESSION, cm, *args, **kwargs) as ressource:
            yield ressource


def new_scope(manager: SyncManager) -> DictProxy:
    """Define a scope and its resources in a variable shared among all processes."""
    scope = manager.dict()
    scope["count"] = 0  # number of possible occurrence for this scope
    scope["lock"] = manager.Lock()  # to update the "count" value
    scope["ressources"] = manager.dict()  # all the ressources created this scope
    return scope


def prepare_scopes(test_plan: TestPlan, manager: SyncManager) -> DictProxy:
    """Prepare a list of all possible scopes and store them in a variable shared among all processes."""

    scopes = manager.dict()

    # The scopes are retrieved from the test plan.

    for tests in test_plan:
        for test in tests:
            for scope_category, scope in test.scopes.items():

                if scope not in scopes:
                    scopes[scope] = new_scope(manager)

                scopes[scope]["count"] += 1

    return scopes


def manage_ressources(scopes):

    global global_queue

    ressources = {}

    while scopes[LYMBO_TEST_SCOPE_SESSION]["count"] > 0:
        time.sleep(0.2)

        # setup ressource
        while not global_queue.empty():

            try:
                message = global_queue.get(block=False)
            except queue.Empty:
                continue

            try:
                module_name = message["ressource"]["module_name"]
                module_path = Path(message["ressource"]["module_path"])
                name = message["ressource"]["name"]
                args = message["ressource"]["args"]
                kwargs = message["ressource"]["kwargs"]
                scope = scopes[message["scope_id"]]

                syspath = sys.path + [
                    str(module_path.parent.absolute()),
                ]

                with patch.object(sys, "path", syspath):

                    module = importlib.import_module(module_name)

                    ctxmgr = getattr(module, name)

                    cm = ctxmgr(*args, **kwargs)

                    scope["ressources"][message["ressource"]["id"]] = pickle.dumps(
                        cm.__enter__()
                    )

                    # we save the context manager to execute the teardown method when the scope count =0
                    ressources[message["scope_id"]] = ressources.get(
                        message["scope_id"], []
                    )
                    ressources[message["scope_id"]].append(cm)

            except Exception as ex:
                print(f"message get failed {ex}")

            # free ressouces
            teardown_ressources(scopes, ressources)

        # free ressouces
        teardown_ressources(scopes, ressources)

    # free ressouces
    teardown_ressources(scopes, ressources)


def teardown_ressources(scopes, ressources):

    released_scopes = []

    for scope_id, ressources_by_scope in ressources.items():
        if scopes[scope_id]["count"] == 0:
            for ressource in ressources_by_scope:
                ressource.__exit__(None, None, None)  # TODO pass execption if necessary
            released_scopes.append(scope_id)

    released_scopes = set(released_scopes)

    for scope_id in released_scopes:
        del ressources[scope_id]


def unset_scope(scopes, test_item: TestItem):

    for scope_id in test_item.scopes.values():
        scope = scopes[scope_id]
        with scope["lock"]:
            scope["count"] -= 1


def print_scopes(scopes: DictProxy):
    print("#" * 30)
    for k, v in scopes.items():
        print(f"{k} -> {v['count']}")
    print("#" * 30)
