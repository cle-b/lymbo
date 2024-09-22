import lymbo
from lymbo import args
from lymbo import expand
from lymbo import scope_class
from lymbo import scope_function
from lymbo import scope_global
from lymbo import scope_module

from cm import resource_cm


@lymbo.test()
def no_scope():
    with resource_cm() as value:
        print('{"scope": "none", "value": "' + str(value) + '"}')


@lymbo.test()
def no_scope2():
    with resource_cm() as value:
        print('{"scope": "none", "value": "' + str(value) + '"}')


@lymbo.test(args(r=expand(1, 2, 3, 4, 5, 6, 7, 8)))
def scope_global_m(r):
    with scope_global(resource_cm) as value:
        print('{"scope": "global", "value": "' + str(value) + '"}')


@lymbo.test()
def scope_module_1():
    with scope_module(resource_cm) as value:
        print('{"scope": "module_b", "value": "' + str(value) + '"}')


@lymbo.test()
def scope_module_2():
    with scope_module(resource_cm) as value:
        print('{"scope": "module_b", "value": "' + str(value) + '"}')


@lymbo.test(args(r=expand(1, 2, 3)))
def scope_function_1(r):
    with scope_function(resource_cm) as value:
        print('{"scope": "function_b_1", "value": "' + str(value) + '"}')


class test_class:

    @staticmethod
    @lymbo.test()
    def scope_module_3():
        with scope_module(resource_cm) as value:
            print('{"scope": "module_b", "value": "' + str(value) + '"}')

    @staticmethod
    @lymbo.test()
    def test_in_class_1():
        with scope_class(resource_cm) as value:
            print('{"scope": "class_b_1", "value": "' + str(value) + '"}')

    @lymbo.test()
    def test_in_class_2(self):
        with scope_class(resource_cm) as value:
            print('{"scope": "class_b_1", "value": "' + str(value) + '"}')


class test_class2:

    @lymbo.test()
    def scope_module_3(self):
        with scope_global(resource_cm) as value:
            print('{"scope": "global", "value": "' + str(value) + '"}')

    @lymbo.test()
    def test_in_class_1(self):
        with scope_class(resource_cm) as value:
            print('{"scope": "class_b_2", "value": "' + str(value) + '"}')

    @staticmethod
    @lymbo.test(args(r=expand(1, 2, 3)))
    def test_in_class_2(r):
        with scope_class(resource_cm) as value:
            print('{"scope": "class_b_2", "value": "' + str(value) + '"}')

    @staticmethod
    @lymbo.test()
    def scope_function2():
        with scope_function(resource_cm) as value:
            print('{"scope": "function_b_2", "value": "' + str(value) + '"}')
