import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # Conversion tests may override the shared FX rate table; make sure
        # every test starts from the published rates and leaves them intact
        # for whatever runs next (e.g. the ledger suite).
        rates.reset_rates()

    def tearDown(self):
        # Restore the published table so a runtime override (set_rate) in one
        # test doesn't leak into another test via the module-level cache.
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
