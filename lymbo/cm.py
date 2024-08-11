import contextlib
import os

from lymbo.env import LYMBO_TEST_COLLECTION


@contextlib.contextmanager
def test(args=None):
    yield


def args(*args, **kwargs):
    """
    Define the parameters used to call the test function.

    If a parameter is defined using the `lymbo.cm.params` function,
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


class ArgParams:

    def __init__(self, *args):
        self.args = list(*args)


def params(*args) -> ArgParams:
    return ArgParams(args)
