import unittest
from decimal import Decimal

import rates
from ledger import Ledger


class TestLedger(unittest.TestCase):
    def setUp(self):
        # total_usd() reads the process-global rate table, so pin it to the
        # published rates. Without this these tests pass or fail depending on
        # which other test module ran first.
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

    def test_total_is_isolated_from_leaked_rate_overrides(self):
        # Regression guard for the CI failure: an FX override leaked from
        # another test module used to make this total 10 cents high.
        rates.set_rate("EUR", "1.1001")
        rates.reset_rates()
        book = Ledger().add("500.00", "USD").add("1000.00", "EUR")
        self.assertEqual(book.total_usd(), Decimal("1600.00"))
