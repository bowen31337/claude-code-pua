import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def tearDown(self):
        # This test mutates the module-level FX cache; restore it so we
        # don't leak a 4-dp EUR rate into later test modules (e.g. the
        # ledger total test, which assumes the published 1.10 rate).
        rates.reset_rates()

    def test_published_rate(self):
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_to_usd(self):
        self.assertEqual(rates.to_usd(Decimal("100"), "USD"), Decimal("100"))

    def test_set_rate_accepts_high_precision(self):
        # The FX job pushes 4-dp rates; make sure they survive round-trip
        # without being truncated to 2 places.
        rates.set_rate("EUR", "1.1001")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
