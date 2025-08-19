"""Tests for the cli dump subcommand"""

# pylint: disable=missing-docstring,unused-argument

import argparse
import io
import json
import tarfile as tar
from pathlib import Path
from typing import Any, cast
from unittest import TestCase, mock

import gbp_testkit.fixtures as testkit
from gbp_testkit.helpers import parse_args, print_command
from gbpcli.types import Console
from gbpcli.utils import EPOCH
from gentoo_build_publisher import publisher
from unittest_fixtures import Fixtures, given, where

from gbp_archive.cli.dump import handler

from . import lib


@given(testkit.publisher, lib.builds, testkit.console, testkit.tmpdir, lib.cd)
@given(stdout=testkit.patch)
@where(stdout__target="gbp_archive.cli.dump.sys.stdout")
@given(argparse_stdout=testkit.patch)
@where(argparse_stdout__target="argparse._sys.stdout")
class DumpTests(TestCase):
    def test_dump_all(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path}"
        args = parse_args(cmdline)

        status = dump(args, fixtures.console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())
        self.assertEqual(6, len(records(path)))

    def test_given_machine(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} lighthouse"
        args = parse_args(cmdline)

        status = dump(args, fixtures.console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())
        self.assertEqual(3, len(records(path)))

    def test_given_build(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} {build}"
        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(0, status, console.err.file.getvalue())
        self.assertTrue(path.exists())

        self.assertEqual(1, len(records(path)))

    def test_given_build_tag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]
        publisher.publish(build)

        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} {build.machine}@"

        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(0, status, console.err.file.getvalue())
        self.assertTrue(path.exists())

        self.assertEqual(1, len(records(path)))

    def test_given_build_tag_does_not_exist(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]
        publisher.publish(build)

        path = Path("test.tar")
        buildspec = f"{build.machine}@bogus"
        cmdline = f"gbp dump -f {path} {buildspec}"

        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(1, status)
        self.assertFalse(path.exists())
        self.assertEqual(f"{buildspec} not found.\n", console.err.file.getvalue())

    def test_dump_to_stdout(self, fixtures: Fixtures) -> None:
        cmdline = "gbp dump"
        args = parse_args(cmdline)
        fixtures.stdout.buffer = io.BytesIO()

        status = dump(args, fixtures.console)

        self.assertEqual(0, status)
        path = Path("test.tar")

        with path.open("wb") as fp:
            fp.write(fixtures.stdout.buffer.getvalue())

        self.assertEqual(6, len(records(path)))

    def test_verbose_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        builds.sort(key=lambda build: (build.machine, build.build_id))
        fixtures.stdout.buffer = io.BytesIO()

        cmdline = "gbp dump -v"
        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(0, status)
        expected = (
            ""
            + "\n".join(f"dumping records for {build}" for build in builds)
            + "\n"
            + "\n".join(f"dumping storage for {build}" for build in builds)
            + "\n"
        )

        self.assertEqual(expected, console.err.file.getvalue())

    def test_build_id_not_found(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f{path} bogus.99"
        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(1, status)
        self.assertEqual("bogus.99 not found.\n", console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_machine_not_found(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} bogus"
        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(1, status)
        self.assertEqual("bogus not found.\n", console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_newer_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds

        for build in builds[:2]:
            record = publisher.repo.build_records.get(build)
            publisher.repo.build_records.save(record, completed=EPOCH)

        path = Path("test.tar")
        cmdline = f"gbp dump -N 2025-02-22 -f{path}"
        args = parse_args(cmdline)
        console = fixtures.console

        status = dump(args, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(4, len(records(path)))

    def test_list_flag(self, fixtures: Fixtures) -> None:
        cmdline = "gbp dump --list lighthouse"

        args = parse_args(cmdline)
        console = fixtures.console
        print_command(cmdline, console)

        status = dump(args, console)

        self.assertEqual(0, status)

        output = console.out.file.getvalue()
        lines = output.strip().split("\n")[1:]
        self.assertEqual(3, len(lines))
        self.assertTrue(all(i.startswith("lighthouse.") for i in lines))

    def test_help_flag(self, fixtures: Fixtures) -> None:
        cmdline = "gbp dump --help"
        console = fixtures.console
        fixtures.argparse_stdout.write = console.out.print

        console.out.print(f"[green]$ [/green]{cmdline}")
        with self.assertRaises(SystemExit):
            parse_args(cmdline)


def dump(args: argparse.Namespace, console: Console) -> int:
    """Call the dump handler with a mock gbp instance"""
    return handler(args, mock.Mock(), console)


def records(path: Path) -> list[dict[str, Any]]:
    """Return the number of records in the dump file given by path"""
    with tar.open(path) as tarfile:
        members = tarfile.getnames()

        if "records.json" not in members:
            return []

        member = tarfile.extractfile("records.json")
        assert member is not None
        with member:
            return cast(list[dict[str, Any]], json.load(member))
