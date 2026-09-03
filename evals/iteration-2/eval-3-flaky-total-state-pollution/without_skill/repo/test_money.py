import unittest
from decimal import Decimal

from money import format_money, round_money


class TestMoney(unittest.TestCase):
    def test_round_down(self):
        self.assertEqual(round_money(Decimal("1.234")), Decimal("1.23"))

    def test_round_up(self):
        self.assertEqual(round_money(Decimal("1.236")), Decimal("1.24"))

    def test_round_half_cent_goes_up_not_to_even(self):
        # Half away from zero, per the documented invoicing contract.
        # Banker's rounding would give 1.00 / 1.02 / 0.12 here.
        self.assertEqual(round_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(round_money(Decimal("1.025")), Decimal("1.03"))
        self.assertEqual(round_money(Decimal("0.125")), Decimal("0.13"))

    def test_format(self):
        self.assertEqual(format_money(Decimal("1234.5")), "$1,234.50")
