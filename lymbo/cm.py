import contextlib
from dataclasses import dataclass
import os
import re
from typing import Any
from typing import Type
from typing import Optional
from typing import Union

from lymbo.env import LYMBO_TEST_COLLECTION


@contextlib.contextmanager
def test(args=None, expected=None):
    yield


def args(*args, **kwargs):
    """
    Define the parameters used to call the test function.

    If a parameter is defined using the `lymbo.expand` function,
    the resulting list is flattened before being passed to the test function.
    """

    if LYMBO_TEST_COLLECTION in os.environ:

        flattened_params = [(args, kwargs)]

        pos = 0
        for arg in args:
            if type(arg) is ArgParams:
                new_flattened_params = []
                for elt in arg.args:
                    for params in flattened_params:
                        gargs, gkwargs = params
                        gargs = list(gargs)
                        gargs[pos] = elt
                        gargs = tuple(gargs)
                        new_flattened_params.append((gargs, gkwargs))
                flattened_params = new_flattened_params
            pos += 1

        for key, value in kwargs.items():
            if type(value) is ArgParams:
                new_flattened_params = []
                for elt in value.args:
                    for params in flattened_params:
                        gargs, gkwargs = params
                        gkwargs = gkwargs.copy()
                        gkwargs[key] = elt
                        new_flattened_params.append((gargs, gkwargs))
                flattened_params = new_flattened_params

        return flattened_params


@dataclass
class ExpectedAssertion:
    value: Union[Type[Any], Any] = None
    match: Union[str, None] = None

    def assert_(self, returned_value: Any) -> Optional[str]:
        """
        Compare the value returned by a function with its expected value.

        Return a description of the failure if they don't match, or None if they matched.
        """
        failure: Optional[str] = None

        if self.value:
            if isinstance(self.value, type):
                if type(returned_value) is not self.value:
                    failure = f"Expected type {self.value.__name__}, but got type {type(returned_value).__name__}."
            else:
                if returned_value != self.value:
                    failure = f"Expected value {self.value}, but got {returned_value}."

        if not failure:
            if self.match:
                if not re.match(self.match, str(returned_value)):
                    failure = f"Value '{returned_value}' does not match the expected pattern '{self.match}'."

        return failure


def expected(
    value: Union[Type[Any], Any, None] = None, match: Union[str, None] = None
) -> ExpectedAssertion:
    """
    Define what we expect the function to return.

    - value: The expected type or object value. Can be None.
    - match: A regular expression to match. Can be None.
    """
    return ExpectedAssertion(value, match)


class ArgParams:

    def __init__(self, *args):
        self.args = list(*args)


def expand(*args) -> ArgParams:
    return ArgParams(args)
