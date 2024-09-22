from contextlib import contextmanager
import random

from lymbo import scope_class


@contextmanager
def resource_cm():
    yield random.randint(0, 9999999)


@contextmanager
def resource_nested_class():
    with scope_class(resource_cm) as value:
        yield value

