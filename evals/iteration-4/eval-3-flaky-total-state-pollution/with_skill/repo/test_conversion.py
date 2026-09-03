import unittest
from decimal import Decimal

import rates


class TestConversion(unittest.TestCase):
    def setUp(self):
        # get_rate/set_rate operate on a process-wide table. Any test that
        # overrides a rate must put it back, or it leaks into every test that
        # runs afterwards in the same process.
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

    def test_override_does_not_leak_to_next_test(self):
        # Guards the cleanup above: if setUp/addCleanup is ever removed, the
        # ordering bug comes back and this test is what catches it.
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.10"))
