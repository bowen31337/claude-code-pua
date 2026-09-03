import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # set_rate() writes to a module-level cache that outlives the test.
        # Restore the published table after every test in this class so a
        # runtime override can never leak into another test module.
        rates.reset_rates()
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
        # Regression guard for the CI failure: reset_rates() must actually
        # restore the published table, since test isolation depends on it.
        rates.set_rate("EUR", "9.9999")
        rates.reset_rates()
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))
