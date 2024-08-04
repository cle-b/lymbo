import concurrent.futures
import sys
from unittest.mock import patch

from lymbo.item import TestItem


def run_test_plan(test_plan: list[list[TestItem]]):

    # TODO add a try first to execute long test first
    # TODO shuffle the tests

    with concurrent.futures.ProcessPoolExecutor() as executor:
        executor.map(run_tests, test_plan)


def run_tests(tests: list[TestItem]):

    for test_item in tests:

        path = test_item.path
        name = test_item.fnc
        cls = test_item.cls

        print(f"EXECUTE [{path.parent.absolute()}] {path.name} - {cls} {name}")

        syspath = sys.path + [
            str(path.parent.absolute()),
        ]

        with patch.object(sys, "path", syspath):

            try:
                module = __import__(str(path.name[:-3]))
                if cls:
                    classdef = getattr(module, cls)
                    self = classdef()
                    test_function = getattr(self, name)

                    # test with static method too

                    try:
                        test_function()
                    except Exception as ex:
                        print(
                            f"Exception during execution test ({path} - {name}): [{ex}]"
                        )

                else:
                    test_function = getattr(module, name)

                    try:
                        test_function()
                    except Exception as ex:
                        print(
                            f"Exception during execution test ({path} - {name}): [{ex}]"
                        )

            except Exception as ex:
                print(f"Exception during load test ({path} - {name}): [{ex}]")
