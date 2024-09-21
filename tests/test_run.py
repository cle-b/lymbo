import json
import os
from pathlib import Path
import unittest

from lymbo.collect import collect_tests
from lymbo.item import GroupBy
from lymbo.item import TestStatus
from lymbo.run import run_test_plan
from lymbo.report import TestReport

dir = os.path.dirname(os.path.abspath(__file__))


class TestRunTestPlan(unittest.TestCase):

    # max_workers

    def test_run_max_workers_default(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_run/run_a.py"))], GroupBy.NONE
        )

        _ = TestReport()

        run_test_plan(test_plan)

        workers_pids = []

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                trace = json.loads(test.output.getvalue())
                workers_pids.append(trace["pid"])

        self.assertEqual(len(set(workers_pids)), os.cpu_count())

    def test_run_max_workers_custom(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_run/run_a.py"))], GroupBy.NONE
        )

        _ = TestReport()

        run_test_plan(test_plan, 2)

        workers_pids = []

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                trace = json.loads(test.output.getvalue())
                workers_pids.append(trace["pid"])

        self.assertEqual(len(set(workers_pids)), 2)


class TestTestItemStatus(unittest.TestCase):

    def test_status(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_run/run_status.py"))], GroupBy.MODULE
        )

        _ = TestReport()

        run_test_plan(test_plan, 1)

        status = {}

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                status[test.fnc] = test.status

        with self.subTest("the test passed"):
            self.assertEqual(status["passed"], TestStatus.PASSED)

        with self.subTest("the test is broken"):
            self.assertEqual(status["broken"], TestStatus.BROKEN)

        with self.subTest("the test failed"):
            self.assertEqual(status["failed"], TestStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
