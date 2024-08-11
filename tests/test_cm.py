import unittest.mock
from lymbo.cm import parameters
from lymbo.cm import params
from lymbo.env import LYMBO_TEST_COLLECTION

import os
import unittest


class Testparameters(unittest.TestCase):

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_parameters_default(self):

        flattened_parameters = parameters()

        self.assertEqual(flattened_parameters, [((), {})])

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_parameters_no_param(self):

        flattened_parameters = parameters(123, "hello", name="opt")

        self.assertEqual(flattened_parameters, [((123, "hello"), {"name": "opt"})])

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_parameters_no_param_list(self):

        flattened_parameters = parameters(123, ["hello", "salut"], name=["opt", "glo"])

        self.assertEqual(
            flattened_parameters,
            [((123, ["hello", "salut"]), {"name": ["opt", "glo"]})],
        )

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_parameters_one_param_arg(self):

        flattened_parameters = parameters(123, params("hello", "salut"), name="opt")

        self.assertEqual(
            flattened_parameters,
            [((123, "hello"), {"name": "opt"}), ((123, "salut"), {"name": "opt"})],
        )

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_parameters_one_param_kwarg(self):

        flattened_parameters = parameters(123, "salut", name=params("opt", "glo"))

        self.assertEqual(
            flattened_parameters,
            [((123, "salut"), {"name": "opt"}), ((123, "salut"), {"name": "glo"})],
        )

    @unittest.mock.patch.dict(os.environ, {LYMBO_TEST_COLLECTION: "1"})
    def test_parameters_many_params(self):

        flattened_parameters = parameters(
            123, params("salut", "hello", "ciao"), name=params("opt", "glo")
        )

        self.assertCountEqual(
            flattened_parameters,
            [
                ((123, "salut"), {"name": "opt"}),
                ((123, "salut"), {"name": "glo"}),
                ((123, "hello"), {"name": "opt"}),
                ((123, "hello"), {"name": "glo"}),
                ((123, "ciao"), {"name": "opt"}),
                ((123, "ciao"), {"name": "glo"}),
            ],
        )

    def test_parameters_not_in_collect(self):

        self.assertIsNone(
            parameters(123, params("salut", "hello", "ciao"), name=params("opt", "glo"))
        )


if __name__ == "__main__":
    unittest.main()
