import contextlib
import importlib
import inspect
import io
from multiprocessing.managers import DictProxy
from multiprocessing.managers import SyncManager
import os
from pathlib import Path
import pickle
import queue
import sys
import time
import traceback
from typing import Any
from typing import List
from unittest.mock import patch

import lymbo
from lymbo.env import LYMBO_RESOURCE_MANAGER
from lymbo.env import LYMBO_TEST_SCOPE_CLASS
from lymbo.env import LYMBO_TEST_SCOPE_FUNCTION
from lymbo.env import LYMBO_TEST_SCOPE_GLOBAL
from lymbo.env import LYMBO_TEST_SCOPE_MAX
from lymbo.env import LYMBO_TEST_SCOPE_MODULE
from lymbo.exception import LymboExceptionScopeHierarchy
from lymbo.item import TestItem
from lymbo.item import TestPlan
from lymbo.log import logger


@contextlib.contextmanager
def _cm_by_scope(scope_name, cm, *args, **kwargs):

    unique_cm_id = f"{cm.__module__}.{cm.__name__}.{args}.{kwargs}"

    scope = lymbo._shared_scopes[os.environ[scope_name]]

    resource = None
    is_new_resource = False

    with scope["lock"]:  # the lock is only to flag the resource creation

        if unique_cm_id not in scope["resources"]:

            is_new_resource = True

            scope["resources"][unique_cm_id] = None  # resource setup in progress
            scope["resources_output"][unique_cm_id] = ""

            module_name = cm.__module__
            module = importlib.import_module(module_name)
            module_path = inspect.getfile(module)
            environ = os.environ.copy()
            name = cm.__name__
            resource_id = unique_cm_id
            scope_id = os.environ.get(scope_name)

    if is_new_resource:

        if LYMBO_RESOURCE_MANAGER in os.environ:
            # it's a resource manager, create resource

            resource = setup_resource(
                module_name,
                module_path,
                environ,
                name,
                args,
                kwargs,
                lymbo._local_resources,
                resource_id,
                scope,
                scope_id,
            )

        else:
            # it's a worker, sent message to create resource
            lymbo._shared_queue.put(
                {
                    "stop": False,
                    "scope_id": scope_id,
                    "resource": {
                        "id": resource_id,
                        "module_name": module_name,
                        "module_path": module_path,
                        "name": name,
                        "args": args,
                        "kwargs": kwargs,
                        "environ": environ,
                    },
                }
            )

    while (
        scope["resources"][unique_cm_id] is None
    ):  # wait until the resource is created
        time.sleep(0.1)  # TODO infinite loop risk

    if scope["resources_output"][unique_cm_id]:
        print(
            scope["resources_output"][unique_cm_id]
        )  # by printing the output here, it will be added to the test output

    if (
        resource is None
    ):  # no need to unpickle the resource if created in this process just now
        resource = pickle.loads(scope["resources"][unique_cm_id])

    if isinstance(resource, Exception):
        raise resource  # TODO report the original traceback

    yield resource


@contextlib.contextmanager
def scope_global(cm, *args, **kwargs):

    if os.environ[LYMBO_TEST_SCOPE_MAX] in ("module", "class", "function"):
        raise LymboExceptionScopeHierarchy(
            f"You can't share a resource with the scope [global] under a shared resource with the scope [{os.environ[LYMBO_TEST_SCOPE_MAX]}]"
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "global"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_GLOBAL, cm, *args, **kwargs) as resource:
            yield resource


@contextlib.contextmanager
def scope_module(cm, *args, **kwargs):

    if os.environ[LYMBO_TEST_SCOPE_MAX] in ("class", "function"):
        raise LymboExceptionScopeHierarchy(
            f"You can't share a resource with the scope [module] under a shared resource with the scope [{os.environ[LYMBO_TEST_SCOPE_MAX]}]"
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "module"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_MODULE, cm, *args, **kwargs) as resource:
            yield resource


@contextlib.contextmanager
def scope_class(cm, *args, **kwargs):

    if os.environ[LYMBO_TEST_SCOPE_MAX] == "function":
        raise LymboExceptionScopeHierarchy(
            f"You can't share a resource with the scope [class] under a shared resource with the scope [{os.environ[LYMBO_TEST_SCOPE_MAX]}]"
        )

    with patch.dict(os.environ, {LYMBO_TEST_SCOPE_MAX: "class"}):

        with _cm_by_scope(LYMBO_TEST_SCOPE_CLASS, cm, *args, **kwargs) as resource:
            yield resource


@contextlib.contextmanager
def scope_function(cm, *args, **kwargs):

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


def manage_resources(scopes, shared_queue: queue.Queue):

    # this is a resource manager
    os.environ[LYMBO_RESOURCE_MANAGER] = "1"
    lymbo._shared_queue = shared_queue
    lymbo._shared_scopes = scopes

    lymbo._local_resources = {}

    while scopes[LYMBO_TEST_SCOPE_GLOBAL]["count"] > 0:

        message = shared_queue.get()

        if message["stop"]:
            break  # all the tests have been executed

        # setup resource
        try:
            module_name = message["resource"]["module_name"]
            module_path = message["resource"]["module_path"]
            name = message["resource"]["name"]
            args = message["resource"]["args"]
            kwargs = message["resource"]["kwargs"]
            environ = message["resource"]["environ"]
            resource_id = message["resource"]["id"]
            scope_id = message["scope_id"]
            scope = scopes[scope_id]

            setup_resource(
                module_name,
                module_path,
                environ,
                name,
                args,
                kwargs,
                lymbo._local_resources,
                resource_id,
                scope,
                scope_id,
            )

        except Exception as ex:
            logger().debug(
                f"manage_resources - exception during the instatiation of a resource for {scope_id} -> "
                f"resource=[{module_name}.{name}({args}{kwargs}] Exception=[{ex}]"
            )

        # free resources
        teardown_resources(scopes, lymbo._local_resources)

    # free resources
    teardown_resources(scopes, lymbo._local_resources)


def setup_resource(
    module_name: str,
    module_path: str,
    environ: List[str],
    name: str,
    args,
    kwargs,
    resources: dict,
    resource_id: str,
    scope: DictProxy,
    scope_id: str,
) -> Any:

    syspath = sys.path + [
        str(Path(module_path).parent.absolute()),
    ]

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

        scope["resources"][resource_id] = pickle.dumps(resource)

        sys.stdout = original_stdout
        sys.stderr = original_stderr

        scope["resources_output"][resource_id] = stdout.getvalue()

        # we save the context manager to execute the teardown method when the scope count =0
        resources[scope_id] = resources.get(scope_id, [])
        resources[scope_id].append(cm)

        return resource


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
