import lymbo
from lymbo import args

import os

@lymbo.test(args(name="clément"))
def hello(name):
    print(f"hello {os.getpid()} {name}")

@lymbo.test()
def hello2(name):
    print(f"hello2 {os.getpid()}")

class MyClass:

    @lymbo.test()
    def coucou(self):
        print(f"coucou {os.getpid()}")

    @lymbo.test()
    def coucou2(self):
        print(f"coucou2 {os.getpid()}")
