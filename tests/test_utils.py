"""Tests for gbp-archive utilities"""

# pylint: disable=missing-docstring
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from gbp_testkit import TestCase

from gbp_archive import utils


class DataclassConversionTests(TestCase):
    """Tests both decode_to and convert_to"""

    def test(self) -> None:
        @dataclass
        class MyDataclass:
            name: str
            balance: Decimal
            due: dt.date

        @utils.convert_to(MyDataclass, "balance")
        def _(value: str) -> Decimal:
            return Decimal(value)

        @utils.convert_to(MyDataclass, "due")
        def _(value: str) -> dt.date:
            return dt.date.fromisoformat(value)

        data = {"name": "marduk", "balance": "5.00", "due": "2025-02-16"}
        result = utils.decode_to(MyDataclass, data)

        expected = MyDataclass("marduk", Decimal("5.00"), dt.date(2025, 2, 16))
        self.assertEqual(expected, result)
