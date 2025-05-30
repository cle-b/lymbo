# To check if an argument has been defined or not
class _UNDEFINED:
    pass


def undefined():
    return _UNDEFINED()


def is_defined(arg) -> bool:
    return not isinstance(arg, _UNDEFINED)
