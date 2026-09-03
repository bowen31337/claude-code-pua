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

    def test_half_cent_rounds_away_from_zero(self):
        # Documented contract: a customer-facing total must never round a
        # half-cent down. Builtin round() would give 1.00 here.
        self.assertEqual(round_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(round_money(Decimal("0.125")), Decimal("0.13"))
        self.assertEqual(round_money(Decimal("-1.005")), Decimal("-1.01"))

    def test_result_always_has_two_places(self):
        self.assertEqual(str(round_money(Decimal("1"))), "1.00")
        self.assertEqual(str(round_money(1.005)), "1.01")
