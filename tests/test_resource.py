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


class TestResource(unittest.TestCase):

    def assert_same_resource(self, resources, scope, nb):
        self.assertEqual(len(resources[scope]), nb, resources[scope])
        self.assertEqual(len(set(resources[scope])), 1, resources[scope])

    def test_resource(self):

        test_plan = collect_tests(
            [
                Path(os.path.join(dir, "data_resource/resource_a.py")),
                Path(os.path.join(dir, "data_resource/resource_b.py")),
            ],
            GroupBy.NONE,
        )

        _ = TestReport()

        run_test_plan(test_plan)

        resources = {}

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                resource = json.loads(test.output.getvalue())
                resources[resource["scope"]] = resources.get(resource["scope"], [])
                resources[resource["scope"]].append(resource["value"])

        with self.subTest("use context manager without scope"):
            # all the resources are unique
            self.assertEqual(len(set(resources["none"])), 4, resources["none"])

        with self.subTest("use context manager with scope function"):
            # all the resources under the same scope are identical
            self.assert_same_resource(resources, "function_a_1", 4)
            self.assert_same_resource(resources, "function_a_2", 3)
            self.assert_same_resource(resources, "function_b_1", 3)
            self.assert_same_resource(resources, "function_b_2", 1)

        with self.subTest("use context manager with scope class"):
            # all the resources under the same scope are identical
            self.assert_same_resource(resources, "class_a_1", 2)
            self.assert_same_resource(resources, "class_a_2", 2)
            self.assert_same_resource(resources, "class_b_1", 2)
            self.assert_same_resource(resources, "class_b_2", 4)

        with self.subTest("use context manager with scope module"):
            # all the resources under the same scope are identical
            self.assert_same_resource(resources, "module_a", 6)
            self.assert_same_resource(resources, "module_b", 3)

        with self.subTest("use context manager with scope global"):
            # all the resources under the same scope are identical
            self.assert_same_resource(resources, "global", 10)

    def test_resource_hierarchy(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_resource/resource_nested.py"))],
            GroupBy.NONE,
            "scope_nested_hierarchy",
        )

        _ = TestReport()

        run_test_plan(test_plan)

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                output = test.output.getvalue()
                self.assertEqual(output, "ok")

    def test_resource_forbidden(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_resource/resource_nested.py"))],
            GroupBy.NONE,
            "scope_nested_forbidden",
        )

        _ = TestReport()

        run_test_plan(test_plan)

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                self.assertEqual(test.status, TestStatus.BROKEN)
                self.assertIn("You can't share a resource with the scope", test.reason)

    def test_resource_nested(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_resource/resource_nested.py"))],
            GroupBy.NONE,
            "scope_nested_shared_resource",
        )

        _ = TestReport()

        run_test_plan(test_plan)

        resources = {}

        for group in test_plan:
            for test in group:
                test.refresh_from_report()
                resource = json.loads(test.output.getvalue())
                resources[resource["scope"]] = resources.get(resource["scope"], [])
                resources[resource["scope"]].append(resource["value"])

        self.assert_same_resource(resources, "nested", 3)


if __name__ == "__main__":
    unittest.main()
