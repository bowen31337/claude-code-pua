import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # Each test must start from the published rate table so runtime
        # overrides never leak into other test files.
        rates.reset_rates()

    def tearDown(self):
        # Restore the published table after every test so a set_rate()
        # override here can't corrupt global state for later suites.
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
