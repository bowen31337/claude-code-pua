import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # The FX job and ops tooling mutate the shared rate table at
        # runtime, so any override here would leak into later test files
        # (e.g. test_ledger's multi-currency total). Always restore.
        self._saved = dict(rates._RATE_CACHE)

    def tearDown(self):
        rates._RATE_CACHE.clear()
        rates._RATE_CACHE.update(self._saved)

    def test_published_rate(self):
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_to_usd(self):
        self.assertEqual(rates.to_usd(Decimal("100"), "USD"), Decimal("100"))

    def test_set_rate_accepts_high_precision(self):
        # The FX job pushes 4-dp rates; make sure they survive round-trip
        # without being truncated to 2 places.
        rates.set_rate("EUR", "1.1001")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
