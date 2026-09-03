from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def round_money(amount):
    """Round a monetary amount to 2 places, half away from zero.

    Half-up matters for invoicing: a customer-facing total must never
    round a half-cent down, or the books disagree with the statement.

    Note: the builtin round() is *not* usable here. round(Decimal, 2)
    delegates to Decimal.__round__, which uses the decimal context's
    default ROUND_HALF_EVEN (banker's rounding), so exact halves land on
    the even digit -- 1.225 -> 1.22, the exact half-cent-down this
    function is documented to prevent. quantize() with an explicit
    rounding mode is the only way to pin the behaviour.
    """
    if not isinstance(amount, Decimal):
        # str() first: Decimal(0.1) would inherit the binary float error.
        amount = Decimal(str(amount))
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def format_money(amount, symbol="$"):
    return f"{symbol}{round_money(amount):,.2f}"
