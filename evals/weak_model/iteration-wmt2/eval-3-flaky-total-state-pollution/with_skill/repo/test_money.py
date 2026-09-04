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
