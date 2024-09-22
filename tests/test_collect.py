import os
from pathlib import Path
import unittest

from lymbo.collect import collect_tests
from lymbo.collect import extract_words_from_filter
from lymbo.collect import match_filter
from lymbo.exception import LymboExceptionFilter
from lymbo.item import GroupBy

dir = os.path.dirname(os.path.abspath(__file__))


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

    # filters

    def test_extract_words(self):

        params = {
            "abc": ["abc"],
            "not abc": ["abc"],
            "not (abc)": ["abc"],
            "(not abc)": ["abc"],
            "abc or abc": ["abc"],
            "abc or abcdef": ["abc", "abcdef"],
            "abc or def": ["abc", "def"],
            "abc and def": ["abc", "def"],
            "abc or (def and ijk)": ["abc", "def", "ijk"],
            "abc or not (def and ijk)": ["abc", "def", "ijk"],
            "(  abc or ((def and (ijk))    )": ["abc", "def", "ijk"],
        }

        for filter, words in params.items():
            with self.subTest(f'filter="{filter}" words={words}'):
                self.assertListEqual(
                    sorted(extract_words_from_filter(filter)), sorted(words)
                )

    def test_match_filter(self):

        params = {
            "abc": "abc",
            "abc/def/ijk.py::func1": "abc",
            "abc/def/ijk.py::func2": "abc or abcdef",
            "abc/def/ijk.py::func3": "abcdef or abc",
            "abc/def/ijk.py::func4": "def",
            "abc/def/ijk.py::func5": "abc and def",
            "abc/def/ijk.py::func6": "abc and def and not ABC",
        }

        for item, filter in params.items():
            with self.subTest(f'item="{item}" filter="{filter}"'):
                self.assertTrue(match_filter(item, filter))

    def test_match_filter_not_match(self):

        params = {
            "abc": "def",
            "abc/def/ijk.py::func1": "ABC",
            "abc/def/ijk.py::func2": "abc and abcdef",
            "abc/def/ijk.py::func3": "abcdef and abc",
            "abc/def/ijk.py::func4": "not def",
            "abc/def/ijk.py::func5": "abc and not def",
            "abc/def/ijk.py::func6": "not abc or (DEF and not ABC)",
        }

        for item, filter in params.items():
            with self.subTest(f'item="{item}" filter="{filter}"'):
                self.assertFalse(match_filter(item, filter))

    def test_collect_tests_filter(self):

        test_plan = collect_tests(
            [Path(os.path.join(dir, "data_collect"))],
            GroupBy.MODULE,
            "second and not ((p=4) or (p=5))",
        )

        self.assertEqual(test_plan.count, (5, 2))

    def test_collect_tests_broken(self):

        try:
            _ = collect_tests(
                [Path(os.path.join(dir, "data_collect"))], GroupBy.MODULE, "second )"
            )
            self.assertFalse(True, "No exception has been raised.")
        except Exception as ex:
            self.assertIsInstance(ex, LymboExceptionFilter)


if __name__ == "__main__":
    unittest.main()
