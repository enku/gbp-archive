"""Tests for gbp-archive utilities"""

# pylint: disable=missing-docstring
import datetime as dt
import tarfile as tar
from dataclasses import dataclass
from decimal import Decimal

from gbp_testkit import TestCase
from unittest_fixtures import Fixtures, given, where

from gbp_archive import utils

from . import lib


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
        def _(value: str) -> dt.date:  # pylint: disable=function-redefined
            return dt.date.fromisoformat(value)

        data = {"name": "marduk", "balance": "5.00", "due": "2025-02-16"}
        result = utils.decode_to(MyDataclass, data)

        expected = MyDataclass("marduk", Decimal("5.00"), dt.date(2025, 2, 16))
        self.assertEqual(expected, result)


@given(lib.tarfile)
@where(**{"tarfile__dir/test.txt": b"test"})
class TarfileExtractTests(TestCase):
    def test(self, fixtures: Fixtures) -> None:
        tarfile = fixtures.tarfile

        fp = utils.tarfile_extract(tarfile, "dir/test.txt")

        self.assertEqual(b"test", fp.read())

    def test_directory_member(self, fixtures: Fixtures) -> None:
        tarfile = fixtures.tarfile

        with self.assertRaises(tar.ReadError):
            utils.tarfile_extract(tarfile, "dir")

    def test_read_error(self, fixtures: Fixtures) -> None:
        tarfile = fixtures.tarfile
        member = tar.TarInfo("/dev/random")
        member.type = tar.CHRTYPE

        with self.assertRaises(tar.ReadError):
            utils.tarfile_extract(tarfile, member)
