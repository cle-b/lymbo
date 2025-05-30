import lymbo
from lymbo import args
from lymbo import expected


@lymbo.test(args(a=4, b=2), expected(2))
def value_passed(a, b):
    return a / b


@lymbo.test(args(a=4, b=2), expected(1))
def value_failed(a, b):
    return a / b


@lymbo.test(args(a=2, b=2), expected(0))
def value_zero_passed(a, b):
    return a - b


@lymbo.test(args(a=3, b=2), expected(0))
def value_zero_failed(a, b):
    return a - b


@lymbo.test(expected=expected(None))
def value_none_passed():
    return None


@lymbo.test(expected=expected(None))
def value_none_failed():
    return 4


@lymbo.test(expected=expected(False))
def value_false_passed():
    return False


@lymbo.test(expected=expected(False))
def value_false_failed():
    return True


@lymbo.test(args(a=4, b=2), expected(1))
def value_broken(a, b):
    raise NameError("boum")


@lymbo.test(args(a=4, b=2), expected(float))
def type_passed(a, b):
    return a / b


@lymbo.test(args(a=4, b=2), expected(str))
def type_failed(a, b):
    return a / b


@lymbo.test(args(a=4, b=2), expected(int))
def type_broken(a, b):
    raise NameError("boum")


@lymbo.test(args(a=4, b=0), expected(ZeroDivisionError))
def exception_passed(a, b):
    return a / b


@lymbo.test(args(a=4, b=0), expected(NameError))
def exception_failed(a, b):
    return a / b


@lymbo.test(args(name="cle"), expected(match="H.* cle.*"))
def match_passed(name):
    return "Hi cle!"


@lymbo.test(args(name="cle"), expected(match="H.* cle.*"))
def match_failed(name):
    return "Bonjour cle!"


@lymbo.test(args(name="cle"), expected(match="H.* cle.*"))
def match_broken(name):
    raise NameError("boum")
