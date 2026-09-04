import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # The FX rate table is module-global mutable state. Guarantee every
        # test starts from the published table so it can't leak into other
        # test files (e.g. test_ledger's multi-currency total).
        rates.reset_rates()

    def tearDown(self):
        # Restore the published table after each test so a runtime override
        # (like the one below) doesn't persist into the next test.
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
