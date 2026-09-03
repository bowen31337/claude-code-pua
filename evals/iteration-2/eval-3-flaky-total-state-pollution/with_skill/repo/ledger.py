from decimal import Decimal

from money import round_money
from rates import to_usd


class Ledger:
    """A tiny multi-currency ledger. Amounts are stored as entered and
    converted to USD only when a total is requested."""

    def __init__(self):
        self.entries = []

    def add(self, amount, currency="USD"):
        self.entries.append((Decimal(str(amount)), currency))
        return self

    def total_usd(self):
        total = sum((to_usd(a, c) for a, c in self.entries), Decimal("0"))
        return round_money(total)

    def __len__(self):
        return len(self.entries)
