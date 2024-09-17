import json
import random
import os

import lymbo
from lymbo import args
from lymbo import expand


def trace():
    return {"pid": os.getpid(), "random": random.randint(0, 99999999)}


@lymbo.test()
def first_test():
    print(json.dumps(trace()))


@lymbo.test()
def second_test():
    print(json.dumps(trace()))


@lymbo.test(args(r=expand(1, 2, 3, 4, 5)))
def multiple_test(r):
    t = trace()
    t["r"] = r
    print(json.dumps(t))
