import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # These tests exercise set_rate(), which mutates the shared,
        # process-wide FX cache in rates.py. Reset it after every test so a
        # runtime override in one test can't leak into another test module
        # (this is what was making test_multi_currency_total come out 10c high).
        self._cleanup = rates.reset_rates
        self.addCleanup(self._cleanup)

    def test_published_rate(self):
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_to_usd(self):
        self.assertEqual(rates.to_usd(Decimal("100"), "USD"), Decimal("100"))

    def test_set_rate_accepts_high_precision(self):
        # The FX job pushes 4-dp rates; make sure they survive round-trip
        # without being truncated to 2 places.
        rates.set_rate("EUR", "1.1001")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
