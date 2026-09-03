from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def round_money(amount):
    """Round a monetary amount to 2 places, half away from zero.

    Half-up matters for invoicing: a customer-facing total must never
    round a half-cent down, or the books disagree with the statement.

    Note: the builtin round() is NOT equivalent here. On a Decimal it
    defers to the decimal context, which defaults to ROUND_HALF_EVEN
    (banker's rounding), so 1.005 would round *down* to 1.00. Quantize
    explicitly instead. Non-Decimal input goes through str() so that
    binary float artifacts don't leak into the result.
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def format_money(amount, symbol="$"):
    return f"{symbol}{round_money(amount):,.2f}"
