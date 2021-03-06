def test_ser():
    from dlex.utils.metrics import ser
    assert ser(
        [1, 1, 0, 1],
        [1, 0, 1, 1], [1]
    ) == 1 / 3
    assert ser(
        [1, 2, 0, 3, 0, 1, 2, 0, 0, 3, 0],
        [2, 2, 0, 3, 0, 1, 3, 0, 0, 3, 0], [1, 2, 3]
    ) == 4 / 6
