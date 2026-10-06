"""Strict input coercion shared by the Python reference evaluators.

The evaluators used to call bool() and Decimal(str()) on whatever they
were handed, so the string "false" counted as true, and NaN, Infinity
and negative sums flowed straight into an award. Every evaluator now
goes through these helpers and fails loudly on anything it cannot read.
"""

from decimal import Decimal, InvalidOperation


def as_bool(mapping, key):
    """mapping[key] as a real bool. Strings and ints are rejected."""
    value = mapping[key]
    if not isinstance(value, bool):
        raise ValueError(
            f"{key} must be true or false, got {value!r} ({type(value).__name__})")
    return value


# Above this the Catala interpreter's JSON output (an IEEE double) can no
# longer hold the value to the fils, and the two paths would disagree.
MAX_MAGNITUDE = Decimal("1e13")


def as_decimal(mapping, key, *, minimum=Decimal(0), maximum=MAX_MAGNITUDE):
    """mapping[key] as a finite Decimal within [minimum, maximum].

    Pass minimum=None for a signed quantity.
    """
    value = mapping[key]
    if isinstance(value, bool):
        raise ValueError(f"{key} must be a number, got a boolean")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{key} must be a number, got {value!r}") from None
    if not number.is_finite():
        raise ValueError(f"{key} must be finite, got {value!r}")
    if minimum is not None and number < minimum:
        raise ValueError(f"{key} must be >= {minimum}, got {value!r}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{key} must be <= {maximum}, got {value!r}")
    return number


def as_choice(mapping, key, allowed):
    """mapping[key] if it is one of `allowed`; unknown values are rejected."""
    value = mapping[key]
    if value not in allowed:
        raise ValueError(f"{key} must be one of {sorted(allowed)}, got {value!r}")
    return value
