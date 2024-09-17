import lymbo


@lymbo.test()
def first_test():
    pass


@lymbo.test()
def second_test():
    pass


class test_class:

    @lymbo.test()
    def test_in_class_1():
        pass

    @lymbo.test()
    def test_in_class_2():
        pass
