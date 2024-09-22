import asyncio
import concurrent.futures
import functools
import queue
import multiprocessing
from multiprocessing.managers import DictProxy
import os
import sys
import time
import traceback
from typing import Optional
from unittest.mock import patch

import lymbo
from lymbo import color
from lymbo.env import LYMBO_TEST_SCOPE_GLOBAL
from lymbo.item import TestItem
from lymbo.item import TestPlan
from lymbo.log import logger
from lymbo.log import trace_call
from lymbo.resource_manager import manage_resources
from lymbo.resource_manager import prepare_scopes
from lymbo.resource_manager import unset_scope


@trace_call
def run_test_plan(test_plan: TestPlan, max_workers: Optional[int] = None) -> int:

    # TODO add a try first to execute long test first
    # TODO shuffle the tests

    tstart = time.time()

    with multiprocessing.Manager() as manager:

        shared_queue: queue.Queue = manager.Queue()

        scopes = prepare_scopes(test_plan, manager)

        run_tests_with_scopes_and_shared_queue = functools.partial(
            run_tests, scopes=scopes, shared_queue=shared_queue
        )
        manage_resources_with_scopes_and_shared_queue = functools.partial(
            manage_resources, scopes=scopes, shared_queue=shared_queue
        )

        if max_workers is None:
            max_workers = os.cpu_count()
            if max_workers is None:
                max_workers = 1

        logger().debug(f"run_test_plan - max_workers={max_workers}")

        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as resources_manager:

            # # Start the resources manager processes
            resources_manager_futures = [
                resources_manager.submit(manage_resources_with_scopes_and_shared_queue)
                for _ in range(max_workers)
            ]

            with concurrent.futures.ProcessPoolExecutor(
                max_workers=max_workers
            ) as tests_executor:
                execresult = tests_executor.map(
                    run_tests_with_scopes_and_shared_queue, test_plan
                )

            for worker_result in execresult:
                logger().debug(f"run_test_plan - worker result: [{worker_result}]")

            # should already be 0 but we force this value because this is what stop the resources manager processes
            with scopes[LYMBO_TEST_SCOPE_GLOBAL]["lock"]:
                scopes[LYMBO_TEST_SCOPE_GLOBAL]["count"] = 0

            for _ in range(max_workers if max_workers else 4):
                shared_queue.put_nowait({"stop": True})

            # Wait for a maximum of 30 seconds for all resource managers to complete
            try:
                for future in concurrent.futures.as_completed(
                    resources_manager_futures, timeout=30
                ):
                    try:
                        resource_manager_result = future.result()
                        logger().debug(
                            f"run_test_plan - resource manager result: [{resource_manager_result}]"
                        )
                    except concurrent.futures.TimeoutError:
                        logger().debug(
                            "run_test_plan - A resource manager process timed out while waiting for completion."
                        )
                    except Exception as e:
                        logger().debug(
                            f"run_test_plan - An error occurred while waiting the resource manager processes. exception=[{e}]"
                        )
            except concurrent.futures.TimeoutError:
                logger().debug(
                    "run_test_plan - Not all resource manager processes completed within 30 seconds."
                )

        # TODO ensure all the processes have been stopped and the resources released.

    duration = int(time.time() - tstart)

    return duration


def run_tests(tests: list[TestItem], scopes: DictProxy, shared_queue: queue.Queue):
    """Run a group of tests sequentially."""

    # this is a worker
    lymbo._shared_queue = shared_queue
    lymbo._shared_scopes = scopes

    try:

        for test_item in tests:

            try:
                with patch.dict(
                    os.environ,
                    test_item.scopes,
                ):
                    run_test(test_item)
            except Exception as ex:
                print("ERROR RUN_F " + str(ex) + "\n" + traceback.format_exc())
            unset_scope(scopes, test_item)

    except Exception as ex:
        print("ERROR RUN_TESTS " + str(ex))


@trace_call
def run_test(test_item: TestItem):

    path = test_item.path
    asynchronous = test_item.asynchronous
    name = test_item.fnc
    cls = test_item.cls
    args, kwargs = test_item.parameters

    print(".", end="", flush=True)

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
            if asynchronous:
                asyncio.run(test_function(*args, **kwargs))
            else:
                test_function(*args, **kwargs)
            test_item.end()
            print(f"{color.GREEN}P{color.RESET}", end="", flush=True)
        except AssertionError as ex:
            test_item.end(reason=ex)
            print(f"{color.RED}F{color.RESET}", end="", flush=True)
        except Exception as ex:
            test_item.end(reason=ex)
            print(f"{color.YELLOW}B{color.RESET}", end="", flush=True)
