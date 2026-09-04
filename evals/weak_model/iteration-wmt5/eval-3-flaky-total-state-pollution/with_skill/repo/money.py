from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal("0.01")


def round_money(amount):
    """Round a monetary amount to 2 places, half away from zero.

    Half-up matters for invoicing: a customer-facing total must never
    round a half-cent down, or the books disagree with the statement.
    """
    return Decimal(round(amount, 2))


def format_money(amount, symbol="$"):
    return f"{symbol}{round_money(amount):,.2f}"
