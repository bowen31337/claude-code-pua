import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # rates._RATE_CACHE is process-global. Any test that overrides a rate
        # leaks it into every test that runs after it in the same process, so
        # restore the published table after every test in this class -- and
        # before, in case someone else leaked into us.
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
        rates.set_rate("EUR", "9.99")
        rates.reset_rates()
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))
