from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def round_money(amount):
    """Round a monetary amount to 2 places, half away from zero.

    Half-up matters for invoicing: a customer-facing total must never
    round a half-cent down, or the books disagree with the statement.

    Note: builtin round() on a Decimal uses ROUND_HALF_EVEN (banker's
    rounding), which rounds 1.005 -> 1.00. That contradicts the contract
    above, so quantize explicitly instead.
    """
    if not isinstance(amount, Decimal):
        # str() first: Decimal(1.005) would inherit the binary float error.
        amount = Decimal(str(amount))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def format_money(amount, symbol="$"):
    return f"{symbol}{round_money(amount):,.2f}"
