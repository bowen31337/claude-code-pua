import unittest
from decimal import Decimal

import rates
from ledger import Ledger


class TestLedger(unittest.TestCase):
    def setUp(self):
        # These totals assert against the *published* FX table. Pin it so the
        # result cannot depend on which test module ran first.
        rates.reset_rates()
        self.addCleanup(rates.reset_rates)

    def test_empty_total(self):
        self.assertEqual(Ledger().total_usd(), Decimal("0.00"))

    def test_single_usd_entry(self):
        book = Ledger().add("500.00", "USD")
        self.assertEqual(book.total_usd(), Decimal("500.00"))

    def test_multi_currency_total(self):
        # 500 USD + 1000 EUR @ 1.10 == 500 + 1100 == 1600.00
        book = Ledger().add("500.00", "USD").add("1000.00", "EUR")
        self.assertEqual(book.total_usd(), Decimal("1600.00"))
