import unittest
from decimal import Decimal

import rates
from ledger import Ledger


class TestLedger(unittest.TestCase):
    def setUp(self):
        # Ledger totals read the global FX table, so pin it to the published
        # rates. Without this the expected values below silently depend on
        # whatever ran earlier in the suite.
        rates.reset_rates()
        self.addCleanup(rates.reset_rates)

    def test_empty_total(self):
        self.assertEqual(Ledger().total_usd(), Decimal("0.00"))

    def test_single_usd_entry(self):
        book = Ledger().add("500.00", "USD")
        self.assertEqual(book.total_usd(), Decimal("500.00"))

    def test_multi_currency_total(self):
        # 500 USD + 1000 EUR @ 1.10 == 500 + 1100 == 1600.00
        book = Ledger().add("500.00", "USD").add("1000.00", "EUR")
        self.assertEqual(book.total_usd(), Decimal("1600.00"))

    def test_total_survives_a_leaked_rate_from_an_earlier_test(self):
        """Regression test for the red CI build.

        Simulates exactly what test_conversion used to leave behind (an
        un-reset EUR override) and then runs the real test case through the
        real fixture. Before the fix this produced 1600.10; if the setUp
        guard is ever removed, this fails here with a clear message instead
        of resurfacing as an order-dependent mystery.
        """
        rates.set_rate("EUR", "1.1001")
        self.assertEqual(rates.get_rate("EUR"), Decimal("1.1001"))

        result = TestLedger("test_multi_currency_total").run()

        self.assertTrue(
            result.wasSuccessful(),
            "test_multi_currency_total is not isolated from leaked FX "
            "overrides: %s" % (result.failures or result.errors),
        )
