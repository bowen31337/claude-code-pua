import unittest
from decimal import Decimal

from money import format_money, round_money


class TestMoney(unittest.TestCase):
    def test_round_down(self):
        self.assertEqual(round_money(Decimal("1.234")), Decimal("1.23"))

    def test_round_up(self):
        self.assertEqual(round_money(Decimal("1.236")), Decimal("1.24"))

    def test_exact_half_rounds_up_not_to_even(self):
        # Regression: round(Decimal, 2) used banker's rounding and gave 1.22.
        self.assertEqual(round_money(Decimal("1.225")), Decimal("1.23"))
        self.assertEqual(round_money(Decimal("0.125")), Decimal("0.13"))
        self.assertEqual(round_money(Decimal("1.235")), Decimal("1.24"))

    def test_exact_half_rounds_away_from_zero_when_negative(self):
        self.assertEqual(round_money(Decimal("-1.225")), Decimal("-1.23"))

    def test_result_is_always_two_places(self):
        self.assertEqual(str(round_money(Decimal("5"))), "5.00")

    def test_format(self):
        self.assertEqual(format_money(Decimal("1234.5")), "$1,234.50")
