import concurrent.futures
import functools
from multiprocessing import Manager
from multiprocessing.managers import DictProxy
import os
import sys
import time
import traceback
from unittest.mock import patch

from lymbo.env import LYMBO_TEST_SCOPE_SESSION
from lymbo.item import TestItem
from lymbo.item import TestPlan
from lymbo.ressource import unset_scope
from lymbo.ressource import manage_ressources
from lymbo.ressource import prepare_scopes
from lymbo.ressource import set_scopes


def run_test_plan(test_plan: TestPlan) -> int:

    # TODO add a try first to execute long test first
    # TODO shuffle the tests

    tstart = time.time()

    with Manager() as manager:

        scopes = prepare_scopes(test_plan, manager)

        run_tests_with_scopes = functools.partial(run_tests, scopes=scopes)
        manage_ressources_with_scopes = functools.partial(
            manage_ressources, scopes=scopes
        )

        with concurrent.futures.ProcessPoolExecutor() as ressources_manager:

            # # Start the ressources manager processes
            ressources_manager_futures = [
                ressources_manager.submit(manage_ressources_with_scopes)
                for _ in range(2)  # TODO create one ressource manager per test executor
            ]

            with concurrent.futures.ProcessPoolExecutor() as tests_executor:
                execresult = tests_executor.map(run_tests_with_scopes, test_plan)

            for r in execresult:
                pass  # TODO log result

            # should already be 0 but we force this value because this is what stop the ressources manager processes
            with scopes[LYMBO_TEST_SCOPE_SESSION]["lock"]:
                scopes[LYMBO_TEST_SCOPE_SESSION]["count"] = 0

            # Wait for a maximum of 30 seconds for all ressource managers to complete
            try:
                for future in concurrent.futures.as_completed(
                    ressources_manager_futures, timeout=30
                ):
                    try:
                        _ = future.result()  # TODO log result
                    except concurrent.futures.TimeoutError:
                        print("A process timed out while waiting for completion.")
                    except Exception as e:
                        print(f"An error occurred: {e}")
            except concurrent.futures.TimeoutError:
                print("Not all processes completed within 30 seconds.")

        # TODO ensure all the processes have been stopped and the ressources released.

    duration = int(time.time() - tstart)

    return duration


def run_tests(tests: list[TestItem], scopes: DictProxy):
    """Run a group of tests sequentially."""

    try:
        set_scopes(scopes)

        for test_item in tests:

            try:
                with patch.dict(
                    os.environ,
                    test_item.scopes,
                ):
                    run_test(test_item)
                    unset_scope(scopes, test_item)
            except Exception as ex:
                print("ERROR RUN_F " + str(ex) + "\n" + traceback.format_exc())

    except Exception as ex:
        print("ERROR RUN_TESTS " + str(ex))


def run_test(test_item: TestItem):

    path = test_item.path
    name = test_item.fnc
    cls = test_item.cls
    args, kwargs = test_item.parameters

    print(f"{test_item} is running")

    syspath = sys.path + [
        str(path.parent.absolute()),
    ]

    with patch.object(sys, "path", syspath):

        module = __import__(str(path.name[:-3]))
        if cls:
            classdef = getattr(module, cls)
            self = classdef()
            test_function = getattr(self, name)
        else:
            test_function = getattr(module, name)

        try:
            test_item.start()
            test_function(*args, **kwargs)
            test_item.end()
        except Exception as ex:
            print("##########")
            print(traceback.format_exc())
            test_item.end(reason=ex)

    print(
        f"{test_item} {test_item.status.value} in {test_item.duration:.3f} second{'s' if test_item.duration>1.0 else ''}"
    )
