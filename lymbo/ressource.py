import contextlib
from contextvars import ContextVar
import importlib
import inspect
import io
from multiprocessing import Queue
from multiprocessing.managers import DictProxy
from multiprocessing.managers import SyncManager
import os
from pathlib import Path
import pickle
import queue
import sys
import time
import traceback
from unittest.mock import patch

from lymbo.env import LYMBO_TEST_SCOPE_CLASS
from lymbo.env import LYMBO_TEST_SCOPE_FUNCTION
from lymbo.env import LYMBO_TEST_SCOPE_GLOBAL
from lymbo.env import LYMBO_TEST_SCOPE_MODULE
from lymbo.item import TestItem
from lymbo.item import TestPlan
from lymbo.log import logger


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
            scope["ressources_output"][unique_cm_id] = ""

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

    print(
        scope["ressources_output"][unique_cm_id]
    )  # by printing the output here, it will be added to the test output

    ressource = pickle.loads(scope["ressources"][unique_cm_id])

    if isinstance(ressource, Exception):
        raise ressource  # TODO report the original traceback

    yield ressource


@contextlib.contextmanager
def scope_global(cm, *args, **kwargs):

    with _cm_by_scope(LYMBO_TEST_SCOPE_GLOBAL, cm, *args, **kwargs) as ressource:
        yield ressource


@contextlib.contextmanager
def scope_module(cm, *args, **kwargs):

    with _cm_by_scope(LYMBO_TEST_SCOPE_MODULE, cm, *args, **kwargs) as ressource:
        yield ressource


@contextlib.contextmanager
def scope_class(cm, *args, **kwargs):

    with _cm_by_scope(LYMBO_TEST_SCOPE_CLASS, cm, *args, **kwargs) as ressource:
        yield ressource


@contextlib.contextmanager
def scope_function(cm, *args, **kwargs):

    with _cm_by_scope(LYMBO_TEST_SCOPE_FUNCTION, cm, *args, **kwargs) as ressource:
        yield ressource


def new_scope(manager: SyncManager) -> DictProxy:
    """Define a scope and its resources in a variable shared among all processes."""
    scope = manager.dict()
    scope["count"] = 0  # number of possible occurrence for this scope
    scope["lock"] = manager.Lock()  # to update the "count" value
    scope["ressources"] = manager.dict()  # all the ressources created this scope
    scope["ressources_output"] = (
        manager.dict()
    )  # all the ressources output created this scope
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

    while scopes[LYMBO_TEST_SCOPE_GLOBAL]["count"] > 0:
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
                scope_id = message["scope_id"]
                scope = scopes[scope_id]

                syspath = sys.path + [
                    str(module_path.parent.absolute()),
                ]

                with patch.object(sys, "path", syspath):

                    original_stdout = sys.stdout
                    original_stderr = sys.stderr

                    stdout = io.StringIO()
                    sys.stdout = stdout
                    sys.stderr = stdout

                    module = importlib.import_module(module_name)

                    ctxmgr = getattr(module, name)

                    cm = ctxmgr(*args, **kwargs)

                    try:
                        logger().debug(
                            f"manage_ressources - instantiate a ressource for {scope_id} -> ressource=[{cm.gen.__name__}{cm.gen.gi_frame.f_locals}]"
                        )
                        ressource = cm.__enter__()
                        logger().debug(
                            f"manage_ressources - instantiate a ressource for {scope_id} -> ressource=[{cm.gen.__name__}{cm.gen.gi_frame.f_locals}] done"
                        )
                    except Exception as ex:
                        ressource = ex

                    scope["ressources"][message["ressource"]["id"]] = pickle.dumps(
                        ressource
                    )

                    sys.stdout = original_stdout
                    sys.stderr = original_stderr

                    scope["ressources_output"][
                        message["ressource"]["id"]
                    ] = stdout.getvalue()

                    # we save the context manager to execute the teardown method when the scope count =0
                    ressources[scope_id] = ressources.get(scope_id, [])
                    ressources[scope_id].append(cm)

            except Exception as ex:
                logger().debug(
                    f"manage_ressources - exception during the instatiation of a ressource for {scope_id} -> ressource=[{cm.gen.__name__}{cm.gen.gi_frame.f_locals}] Exception=[{ex}]"
                )

            # free ressouces
            teardown_ressources(scopes, ressources)

        # free ressouces
        teardown_ressources(scopes, ressources)

    # free ressouces
    teardown_ressources(scopes, ressources)


def teardown_ressources(scopes, ressources):

    released_scopes = []

    try:

        for scope_id, ressources_by_scope in ressources.items():
            if scopes[scope_id]["count"] == 0:
                for ressource in ressources_by_scope:
                    try:
                        logger().debug(
                            f"teardown_ressources - teardown ressource for {scope_id} -> ressource=[{ressource.gen.__name__}{ressource.gen.gi_frame.f_locals}]"
                        )
                        original_stdout = sys.stdout
                        original_stderr = sys.stderr

                        stdout = io.StringIO()
                        sys.stdout = stdout
                        sys.stderr = stdout

                        ressource.__exit__(
                            None, None, None
                        )  # TODO pass execption if necessary

                        sys.stdout = original_stdout
                        sys.stderr = original_stderr
                    except Exception as ex:
                        sys.stdout = original_stdout
                        sys.stderr = original_stderr

                        logger().warning(
                            f"An exception occurred during the execution of the resource's teardown. stdout=[{stdout.getvalue()}], exception=[{ex}], traceback={traceback.format_exc()}"
                        )
                released_scopes.append(scope_id)

        released_scopes = set(released_scopes)

        for scope_id in released_scopes:
            del ressources[scope_id]
    except Exception as ex:
        logger().debug(
            f"teardown_ressources exception=[{ex}], traceback={traceback.format_exc()}"
        )


def unset_scope(scopes, test_item: TestItem):

    for scope_id in test_item.scopes.values():
        scope = scopes[scope_id]
        with scope["lock"]:
            scope["count"] -= 1
