import unittest
from decimal import Decimal

from ledger import Ledger


class TestLedger(unittest.TestCase):
    def test_empty_total(self):
        self.assertEqual(Ledger().total_usd(), Decimal("0.00"))

    def test_single_usd_entry(self):
        book = Ledger().add("500.00", "USD")
        self.assertEqual(book.total_usd(), Decimal("500.00"))

    def test_multi_currency_total(self):
        # 500 USD + 1000 EUR @ 1.10 == 500 + 1100 == 1600.00
        book = Ledger().add("500.00", "USD").add("1000.00", "EUR")
        self.assertEqual(book.total_usd(), Decimal("1600.00"))
