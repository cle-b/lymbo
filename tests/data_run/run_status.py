import lymbo


@lymbo.test()
def passed():
    assert True


@lymbo.test()
def broken():
    _ = 1 / 0


@lymbo.test()
def failed():
    assert False
