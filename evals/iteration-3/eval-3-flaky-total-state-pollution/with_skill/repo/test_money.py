import unittest
from decimal import Decimal

from money import format_money, round_money


class TestMoney(unittest.TestCase):
    def test_round_down(self):
        self.assertEqual(round_money(Decimal("1.234")), Decimal("1.23"))

    def test_round_up(self):
        self.assertEqual(round_money(Decimal("1.236")), Decimal("1.24"))

    def test_format(self):
        self.assertEqual(format_money(Decimal("1234.5")), "$1,234.50")

    def test_half_cent_rounds_up_not_to_even(self):
        # The docstring promises half AWAY FROM ZERO. Python's built-in
        # round() on a Decimal is half-to-EVEN, which sent these down.
        self.assertEqual(round_money(Decimal("1.225")), Decimal("1.23"))
        self.assertEqual(round_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(round_money(Decimal("0.005")), Decimal("0.01"))

    def test_half_cent_rounds_away_from_zero_when_negative(self):
        self.assertEqual(round_money(Decimal("-1.225")), Decimal("-1.23"))

    def test_result_is_always_quantized_to_two_places(self):
        self.assertEqual(str(round_money(Decimal("5"))), "5.00")
        self.assertEqual(str(round_money(Decimal("0"))), "0.00")

    def test_accepts_non_decimal_input(self):
        self.assertEqual(round_money("1.235"), Decimal("1.24"))
        self.assertEqual(round_money(2), Decimal("2.00"))
