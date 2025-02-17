"""Tests for gbp-archive utilities"""

# pylint: disable=missing-docstring
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from gbp_testkit import TestCase

from gbp_archive import utils


class SerializableTests(TestCase):
    def test_dataclass(self) -> None:
        @dataclass
        class Balance:
            amount: int
            currency: str

        balance = Balance(5, "USD")

        value = utils.serializable(balance)

        self.assertEqual({"amount": 5, "currency": "USD"}, value)

    def test_datetime(self) -> None:
        timezone = dt.timezone(dt.timedelta(hours=-6), "CST")
        datetime = dt.datetime(2025, 2, 15, 19, 59, tzinfo=timezone)
        expected = "2025-02-15T19:59:00-06:00"

        self.assertEqual(expected, utils.serializable(datetime))

    def test_already_serializable(self) -> None:
        self.assertEqual("hello world", "hello world")


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
