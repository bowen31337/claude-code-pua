import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # rates._RATE_CACHE is process-global module state. Any test that
        # calls set_rate() leaks that override into every test that runs
        # after it, in any file. Restore the published table unconditionally
        # (addCleanup runs even if the test fails or errors).
        rates.reset_rates()
        self.addCleanup(rates.reset_rates)

    def test_published_rate(self):
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_to_usd(self):
        self.assertEqual(rates.to_usd(Decimal("100"), "USD"), Decimal("100"))

    def test_set_rate_accepts_high_precision(self):
        # The FX job pushes 4-dp rates; make sure they survive round-trip
        # without being truncated to 2 places. Scoped so the override cannot
        # escape into another test file.
        with rates.rate_override("EUR", "1.1001"):
            self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_rate_override_restores_on_exception(self):
        with self.assertRaises(RuntimeError):
            with rates.rate_override("EUR", "9.9999"):
                raise RuntimeError("boom")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))

    def test_reset_rates_discards_overrides(self):
        # Guards the cleanup mechanism itself: if reset_rates() ever stops
        # working, this fails here rather than as a mystery failure in
        # whichever test file happens to run next.
        rates.set_rate("EUR", "9.9999")
        rates.reset_rates()
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))
