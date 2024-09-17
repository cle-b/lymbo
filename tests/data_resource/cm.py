from contextlib import contextmanager
import random


@contextmanager
def resource_cm():
    yield random.randint(0, 9999999)
