import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def test_published_rate(self):
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_to_usd(self):
        self.assertEqual(rates.to_usd(Decimal("100"), "USD"), Decimal("100"))

    def test_set_rate_accepts_high_precision(self):
        # set_rate mutates the global FX table; restore it after so we don't
        # leak a 1.1001 EUR rate into later test files (e.g. the ledger total).
        self.addCleanup(rates.reset_rates)
        # The FX job pushes 4-dp rates; make sure they survive round-trip
        # without being truncated to 2 places.
        rates.set_rate("EUR", "1.1001")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
