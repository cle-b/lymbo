import os
from pathlib import Path
import unittest

from lymbo.collect import collect_tests
from lymbo.item import GroupBy

dir = os.path.dirname(os.path.abspath("."))


class TestCollect(unittest.TestCase):

    # group by

    def test_collect_tests_groupby_none(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect"))], GroupBy.NONE
        )

        self.assertEqual(test_plan.count, (11, 11))

    def test_collect_tests_groupby_function(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect"))], GroupBy.FUNCTION
        )

        self.assertEqual(test_plan.count, (11, 6))

    def test_collect_tests_groupby_class(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect"))], GroupBy.CLASS
        )

        self.assertEqual(test_plan.count, (11, 10))

    def test_collect_tests_groupby_module(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect"))], GroupBy.MODULE
        )

        self.assertEqual(test_plan.count, (11, 2))

    # list files

    def test_collect_tests_dir_not_exists(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect_xxxxx"))], GroupBy.NONE
        )

        self.assertEqual(test_plan.count, (0, 0))

    def test_collect_tests_dir(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect"))], GroupBy.NONE
        )

        self.assertEqual(test_plan.count, (11, 11))

    def test_collect_tests_one_file(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect/collect_a.py"))], GroupBy.NONE
        )

        self.assertEqual(test_plan.count, (4, 4))

    def test_collect_tests_two_files(self):

        test_plan = collect_tests(
            [
                Path(os.path.join(dir, "data_collect/collect_a.py")),
                Path(os.path.join(dir, "data_collect/collect_b.py")),
            ],
            GroupBy.NONE,
        )

        self.assertEqual(test_plan.count, (11, 11))


if __name__ == "__main__":
    unittest.main()
