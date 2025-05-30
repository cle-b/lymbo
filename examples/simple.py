import lymbo


@lymbo.test()
def addition():
    assert 1 + 2 == 3, "Addition test failed: 1 + 2 did not equal 3"
