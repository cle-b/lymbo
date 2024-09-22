import lymbo
from lymbo import scope_class
from lymbo import scope_function
from lymbo import scope_global
from lymbo import scope_module

from cm import resource_cm


@lymbo.test()
def scope_nested_hierarchy():
    with scope_global(resource_cm):
        with scope_module(resource_cm):
            with scope_class(resource_cm):
                with scope_function(resource_cm):
                    print("ok", end="")


@lymbo.test()
def scope_nested_forbidden_module_global():

    with scope_module(resource_cm):
        with scope_global(resource_cm):
            pass


@lymbo.test()
def scope_nested_forbidden_class_global():

    with scope_class(resource_cm):
        with scope_global(resource_cm):
            pass


@lymbo.test()
def scope_nested_forbidden_function_global():

    with scope_function(resource_cm):
        with scope_global(resource_cm):
            pass


@lymbo.test()
def scope_nested_forbidden_class_module():

    with scope_class(resource_cm):
        with scope_module(resource_cm):
            pass


@lymbo.test()
def scope_nested_forbidden_function_module():

    with scope_function(resource_cm):
        with scope_module(resource_cm):
            pass


@lymbo.test()
def scope_nested_forbidden_function_class():

    with scope_function(resource_cm):
        with scope_class(resource_cm):
            pass
