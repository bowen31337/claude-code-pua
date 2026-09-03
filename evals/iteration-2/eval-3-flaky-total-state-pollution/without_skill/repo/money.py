from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def round_money(amount):
    """Round a monetary amount to 2 places, half away from zero.

    Half-up matters for invoicing: a customer-facing total must never
    round a half-cent down, or the books disagree with the statement.

    Note: the builtin round() applies banker's rounding (half-to-even) to
    Decimal, which rounds half-cents down half the time. Quantize explicitly.
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def format_money(amount, symbol="$"):
    return f"{symbol}{round_money(amount):,.2f}"
