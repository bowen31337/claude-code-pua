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
        # The docstring contract: a half-cent must never round down.
        # Banker's rounding (the builtin round()) fails 1.005 and 1.025.
        self.assertEqual(round_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(round_money(Decimal("1.015")), Decimal("1.02"))
        self.assertEqual(round_money(Decimal("1.025")), Decimal("1.03"))
        self.assertEqual(round_money(Decimal("0.125")), Decimal("0.13"))

    def test_negative_half_cent_rounds_away_from_zero(self):
        self.assertEqual(round_money(Decimal("-1.005")), Decimal("-1.01"))

    def test_result_is_always_quantized_to_two_places(self):
        self.assertEqual(str(round_money(Decimal("0"))), "0.00")
        self.assertEqual(str(round_money(Decimal("1.2"))), "1.20")

    def test_float_input_does_not_leak_binary_artifacts(self):
        self.assertEqual(round_money(1.235), Decimal("1.24"))
        self.assertEqual(format_money(1.005), "$1.01")
