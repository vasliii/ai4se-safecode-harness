from src.calculator import add, divide, multiply, subtract


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(7, 4) == 3


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide():
    assert divide(8, 2) == 4
