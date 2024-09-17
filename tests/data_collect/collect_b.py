import lymbo
from lymbo import args, expand


@lymbo.test()
async def first_test():
    pass


@lymbo.test(args(p=expand(1, 2, 3, 4, 5, 6)))
def second_test(p):
    pass
