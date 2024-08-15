import concurrent.futures
import sys
import time
from unittest.mock import patch

from lymbo.item import TestItem
from lymbo.item import TestPlan


def run_test_plan(test_plan: TestPlan) -> int:

    # TODO add a try first to execute long test first
    # TODO shuffle the tests

    tstart = time.time()

    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(run_tests, test_plan)

    duration = int(time.time() - tstart)

    return duration


def run_tests(tests: list[TestItem]):

    for test_item in tests:

        try:
            run_function(test_item)
        except Exception as ex:
            print("ERROR RUN_F " + str(ex))


def run_function(test_item: TestItem):

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
            test_item.end(reason=ex)

    print(
        f"{test_item} {test_item.status.value} in {test_item.duration:.3f} second{'s' if test_item.duration>1.0 else ''}"
    )
