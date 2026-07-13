from src.calculator import add, subtract


def test_add():
    assert add(2, 3) == 5
    assert add(-4, 9) == 5


def test_subtract():
    assert subtract(9, 4) == 5
