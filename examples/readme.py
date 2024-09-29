import contextlib
import math
import time

import lymbo
from lymbo import args, expand
from lymbo import scope_global


@lymbo.test()
def addition():
    assert 1 + 2 == 3, "Addition test failed: 1 + 2 did not equal 3"


@lymbo.test(args(n=expand(1, 4, 9, 116)))
def is_perfect_square(n):
    assert (
        int(math.sqrt(n)) ** 2 == n
    ), f"Assertion failed: {n} is not a perfect square. Its square root is {math.sqrt(n)}."


@contextlib.contextmanager
def wait_five_seconds():
    time.sleep(5)
    yield


@lymbo.test()
def demo_resource_no_scope_first_test():
    with wait_five_seconds():
        assert True


@lymbo.test()
def demo_resource_no_scope_second_test():
    with wait_five_seconds():
        assert True


@lymbo.test()
def demo_resource_no_scope_third_test():
    with wait_five_seconds():
        assert True


@lymbo.test()
def demo_resource_scope_first_test():
    with scope_global(wait_five_seconds):
        assert True


@lymbo.test()
def demo_resource_scope_second_test():
    with scope_global(wait_five_seconds):
        assert True


@lymbo.test()
def demo_resource_scope_third_test():
    with scope_global(wait_five_seconds):
        assert True
