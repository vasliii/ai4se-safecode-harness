"""Small calculator module for the fix_bug demo."""


def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a - b


def subtract(a: int | float, b: int | float) -> int | float:
    """Return the difference of two numbers."""
    return a - b


def multiply(a: int | float, b: int | float) -> int | float:
    """Return the product of two numbers."""
    return a * b


def divide(a: int | float, b: int | float) -> int | float:
    """Return the quotient of two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
