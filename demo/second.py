import lymbo
import os

@lymbo.test()
def hello():
    print(f"hello {os.getpid()}")

@lymbo.test()
def hello2():
    print(f"hello2 {os.getpid()}")

class MyClass:

    @lymbo.test()
    def coucou(self):
        print(f"coucou {os.getpid()}")

    @lymbo.test()
    def coucou2(self):
        print(f"coucou2 {os.getpid()}")