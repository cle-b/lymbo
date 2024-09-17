import unittest.mock
from lymbo import args
from lymbo import expand
from lymbo.env import LYMBO_TEST_COLLECTION

import os
import unittest


class TestArgs(unittest.TestCase):

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_args_default(self):

        flattened_args = args()

        self.assertEqual(flattened_args, [((), {})])

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_args_no_param(self):

        flattened_args = args(123, "hello", name="opt")

        self.assertEqual(flattened_args, [((123, "hello"), {"name": "opt"})])

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_args_no_param_list(self):

        flattened_args = args(123, ["hello", "salut"], name=["opt", "glo"])

        self.assertEqual(
            flattened_args,
            [((123, ["hello", "salut"]), {"name": ["opt", "glo"]})],
        )

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_args_one_param_arg(self):

        flattened_args = args(123, expand("hello", "salut"), name="opt")

        self.assertEqual(
            flattened_args,
            [((123, "hello"), {"name": "opt"}), ((123, "salut"), {"name": "opt"})],
        )

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_args_one_param_kwarg(self):

        flattened_args = args(123, "salut", name=expand("opt", "glo"))

        self.assertEqual(
            flattened_args,
            [((123, "salut"), {"name": "opt"}), ((123, "salut"), {"name": "glo"})],
        )

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_args_many_params(self):

        flattened_args = args(
            123, expand("salut", "hello", "ciao"), name=expand("opt", "glo")
        )

        self.assertCountEqual(
            flattened_args,
            [
                ((123, "salut"), {"name": "opt"}),
                ((123, "salut"), {"name": "glo"}),
                ((123, "hello"), {"name": "opt"}),
                ((123, "hello"), {"name": "glo"}),
                ((123, "ciao"), {"name": "opt"}),
                ((123, "ciao"), {"name": "glo"}),
            ],
        )

    def test_args_not_in_collect(self):

        self.assertIsNone(
            args(123, expand("salut", "hello", "ciao"), name=expand("opt", "glo"))
        )


if __name__ == "__main__":
    unittest.main()
