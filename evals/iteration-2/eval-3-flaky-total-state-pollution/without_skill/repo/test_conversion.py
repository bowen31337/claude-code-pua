import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # set_rate mutates the process-global rate cache in rates.py. Without
        # this, an override leaks into every test that runs afterwards (it is
        # what made test_ledger.test_multi_currency_total fail in CI but pass
        # when that file was run on its own).
        self.addCleanup(rates.reset_rates)

    def test_published_rate(self):
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_to_usd(self):
        self.assertEqual(rates.to_usd(Decimal("100"), "USD"), Decimal("100"))

    def test_set_rate_accepts_high_precision(self):
        # The FX job pushes 4-dp rates; make sure they survive round-trip
        # without being truncated to 2 places.
        rates.set_rate("EUR", "1.1001")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))

    def test_reset_rates_discards_overrides(self):
        rates.set_rate("EUR", "1.1001")
        rates.reset_rates()
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))
