from typing import Any

ArgParams = list[Any]


def test(args=None):
    def decorator(function):
        def wrapper(*fargs, **fkwargs):

            print(f"ARGS {args} fargs {fargs} fkwargs {fkwargs}")
            if args:
                result = function(*(fargs + args[0]), **(fkwargs | args[1]))
            else:
                result = function(*fargs, **fkwargs)
            return result

        return wrapper

    return decorator


def args(*args, **kwargs):
    return args, kwargs


def params(param: list[Any]) -> ArgParams:
    return param
