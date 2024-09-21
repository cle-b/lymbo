import contextlib
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
from typing import Union
from unittest.mock import patch

from lymbo.env import LYMBO_TEST_SCOPE_CLASS
from lymbo.env import LYMBO_TEST_SCOPE_FUNCTION
from lymbo.env import LYMBO_TEST_SCOPE_GLOBAL
from lymbo.env import LYMBO_TEST_SCOPE_MAX
from lymbo.env import LYMBO_TEST_SCOPE_MODULE
from lymbo.exception import LymboExceptionScopeHierarchy
from lymbo.exception import LymboExceptionScopeNested
from lymbo.item import TestItem
from lymbo.item import TestPlan
from lymbo.log import logger


shared_scopes: Union[DictProxy, None] = None
global_queue: Queue = Queue()


def set_scopes(scopes):
    global shared_scopes
    shared_scopes = scopes


@contextlib.contextmanager
def _cm_by_scope(scope_name, cm, *args, **kwargs):

    global shared_scopes
    scopes = shared_scopes
    global global_queue

    unique_cm_id = f"{cm.__module__}.{cm.__name__}.{args}.{kwargs}"

    scope = scopes[os.environ[scope_name]]
    with scope["lock"]:  # the lock is only for the request about the resource creation

        if unique_cm_id not in scope["resources"]:
            scope["resources"][unique_cm_id] = None
            scope["resources_output"][unique_cm_id] = ""

            module_name = cm.__module__
            module = importlib.import_module(module_name)
            module_path = inspect.getfile(module)

            global_queue.put_nowait(
                {
                    "stop": False,
                    "scope_id": os.environ.get(scope_name),
                    "resource": {
                        "id": unique_cm_id,
                        "module_name": module_name,
                        "module_path": module_path,
                        "name": cm.__name__,
                        "args": args,
                        "kwargs": kwargs,
                        "environ": os.environ.copy(),
                    },
                }
            )

        while scope["resources"][unique_cm_id] is None:
            time.sleep(0.1)  # TODO infinite loop risk

        if scope["resources_output"][unique_cm_id]:
            print(
                scope["resources_output"][unique_cm_id]
            )  # by printing the output here, it will be added to the test output

        resource = pickle.loads(scope["resources"][unique_cm_id])

    if isinstance(resource, Exception):
        raise resource  # TODO report the original traceback

    yield resource


@contextlib.contextmanager
def scope_global(cm, *args, **kwargs):

    if LYMBO_TEST_SCOPE_MAX not in os.environ:
        raise LymboExceptionScopeNested(
            "You can't share a resource in another shared resource."
        )

    if os.environ[LYMBO_TEST_SCOPE_MAX] in ("module", "class", "function"):
        raise LymboExceptionScopeHierarchy(
            f"You can't share a resource with the scope [global] under a shared resource with the scope [{os.environ[LYMBO_TEST_SCOPE_MAX]}]"
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "global"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_GLOBAL, cm, *args, **kwargs) as resource:
            yield resource


@contextlib.contextmanager
def scope_module(cm, *args, **kwargs):

    if LYMBO_TEST_SCOPE_MAX not in os.environ:
        raise LymboExceptionScopeNested(
            "You can't share a resource in another shared resource."
        )

    if os.environ[LYMBO_TEST_SCOPE_MAX] in ("class", "function"):
        raise LymboExceptionScopeHierarchy(
            f"You can't share a resource with the scope [module] under a shared resource with the scope [{os.environ[LYMBO_TEST_SCOPE_MAX]}]"
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "module"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_MODULE, cm, *args, **kwargs) as resource:
            yield resource


@contextlib.contextmanager
def scope_class(cm, *args, **kwargs):

    if LYMBO_TEST_SCOPE_MAX not in os.environ:
        raise LymboExceptionScopeNested(
            "You can't share a resource in another shared resource."
        )

    if os.environ[LYMBO_TEST_SCOPE_MAX] == "function":
        raise LymboExceptionScopeHierarchy(
            f"You can't share a resource with the scope [class] under a shared resource with the scope [{os.environ[LYMBO_TEST_SCOPE_MAX]}]"
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "class"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_CLASS, cm, *args, **kwargs) as resource:
            yield resource


@contextlib.contextmanager
def scope_function(cm, *args, **kwargs):

    if LYMBO_TEST_SCOPE_MAX not in os.environ:
        raise LymboExceptionScopeNested(
            "You can't share a resource in another shared resource."
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "function"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_FUNCTION, cm, *args, **kwargs) as resource:
            yield resource


def new_scope(manager: SyncManager) -> DictProxy:
    """Define a scope and its resources in a variable shared among all processes."""
    scope = manager.dict()
    scope["count"] = 0  # number of possible occurrence for this scope
    scope["lock"] = manager.Lock()  # to update the "count" value
    scope["resources"] = manager.dict()  # all the resources created for this scope
    scope["resources_output"] = (
        manager.dict()
    )  # all the resources output created for this scope
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


def manage_resources(scopes):

    global global_queue

    resources = {}

    while scopes[LYMBO_TEST_SCOPE_GLOBAL]["count"] > 0:

        try:
            message = global_queue.get(timeout=5)
        except queue.Empty:
            continue

        if message["stop"]:
            break  # all the tests have been executed

        # setup resource
        try:
            module_name = message["resource"]["module_name"]
            module_path = Path(message["resource"]["module_path"])
            name = message["resource"]["name"]
            args = message["resource"]["args"]
            kwargs = message["resource"]["kwargs"]
            environ = message["resource"]["environ"]
            scope_id = message["scope_id"]
            scope = scopes[scope_id]

            syspath = sys.path + [
                str(module_path.parent.absolute()),
            ]

            if LYMBO_TEST_SCOPE_MAX in environ:
                del environ[
                    LYMBO_TEST_SCOPE_MAX
                ]  # to detect if we try to create a shared resource from another shared resource

            with (
                patch.object(sys, "path", syspath),
                patch.dict(os.environ, environ),
            ):

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
                        f"manage_resources - instantiate a resource for {scope_id} -> "
                        f"resource=[{module_name}.{name}({args}{kwargs})]"
                    )
                    resource = cm.__enter__()
                    logger().debug(
                        f"manage_resources - instantiate a resource for {scope_id} -> "
                        f"resource=[{module_name}.{name}({args}{kwargs}] done"
                    )
                except Exception as ex:
                    resource = ex

                scope["resources"][message["resource"]["id"]] = pickle.dumps(resource)

                sys.stdout = original_stdout
                sys.stderr = original_stderr

                scope["resources_output"][message["resource"]["id"]] = stdout.getvalue()

                # we save the context manager to execute the teardown method when the scope count =0
                resources[scope_id] = resources.get(scope_id, [])
                resources[scope_id].append(cm)

        except Exception as ex:
            logger().debug(
                f"manage_resources - exception during the instatiation of a resource for {scope_id} -> "
                f"resource=[{module_name}.{name}({args}{kwargs}] Exception=[{ex}]"
            )

        # free resources
        teardown_resources(scopes, resources)

    # free resources
    teardown_resources(scopes, resources)


def teardown_resources(scopes, resources):

    released_scopes = []

    try:

        for scope_id, resources_by_scope in resources.items():
            if scopes[scope_id]["count"] == 0:
                for resource in resources_by_scope:
                    try:
                        logger().debug(
                            f"teardown_resources - teardown resource for {scope_id} -> resource=[{resource}]"
                        )
                        original_stdout = sys.stdout
                        original_stderr = sys.stderr

                        stdout = io.StringIO()
                        sys.stdout = stdout
                        sys.stderr = stdout

                        resource.__exit__(
                            None, None, None
                        )  # TODO pass exception if necessary

                        sys.stdout = original_stdout
                        sys.stderr = original_stderr
                    except Exception as ex:
                        sys.stdout = original_stdout
                        sys.stderr = original_stderr

                        logger().warning(
                            "An exception occurred during the execution of the resource's teardown."
                            f" stdout=[{stdout.getvalue()}], exception=[{ex}], traceback={traceback.format_exc()}"
                        )
                released_scopes.append(scope_id)

        released_scopes = set(released_scopes)

        for scope_id in released_scopes:
            del resources[scope_id]
    except Exception as ex:
        logger().debug(
            f"teardown_resources exception=[{ex}], traceback={traceback.format_exc()}"
        )


def unset_scope(scopes, test_item: TestItem):

    for scope_id in test_item.scopes.values():
        scope = scopes[scope_id]
        with scope["lock"]:
            scope["count"] -= 1
