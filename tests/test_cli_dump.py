"""Tests for the cli dump subcommand"""

# pylint: disable=missing-docstring

import io
import json
import tarfile as tar
from pathlib import Path
from typing import Any, cast
from unittest import TestCase, mock

from gbp_testkit.helpers import parse_args, print_command
from gbpcli.utils import EPOCH
from unittest_fixtures import Fixtures, given

from gbp_archive.cli.dump import handler as dump


@given("publisher", "builds", "console", "tmpdir", "cd")
class DumpTests(TestCase):
    def test_dump_all(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path}"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(6, len(records(path)))

    def test_given_machine(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} lighthouse"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(3, len(records(path)))

    def test_given_build(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]

        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} {build}"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(1, len(records(path)))

    def test_dump_to_stdout(self, fixtures: Fixtures) -> None:
        cmdline = "gbp dump"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        with mock.patch("gbp_archive.cli.dump.sys.stdout") as stdout:
            stdout.buffer = io.BytesIO()
            status = dump(args, gbp, console)

        self.assertEqual(0, status)
        path = Path("test.tar")

        with path.open("wb") as fp:
            fp.write(stdout.buffer.getvalue())

        self.assertEqual(6, len(records(path)))

    def test_verbose_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        builds.sort(key=lambda build: (build.machine, build.build_id))

        cmdline = "gbp dump -v"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        with mock.patch("gbp_archive.cli.dump.sys.stdout") as stdout:
            stdout.buffer = io.BytesIO()
            status = dump(args, gbp, console)

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
        gbp = mock.Mock()
        console = fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(1, status)
        self.assertEqual("bogus.99 not found.\n", console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_machine_not_found(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f {path} bogus"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(1, status)
        self.assertEqual("bogus not found.\n", console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_newer_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        publisher = fixtures.publisher

        for build in builds[:2]:
            record = publisher.repo.build_records.get(build)
            publisher.repo.build_records.save(record, completed=EPOCH)

        path = Path("test.tar")
        cmdline = f"gbp dump -N 2025-02-22 -f{path}"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(4, len(records(path)))

    def test_list_flag(self, fixtures: Fixtures) -> None:
        cmdline = "gbp dump --list lighthouse"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console
        print_command(cmdline, console)

        status = dump(args, gbp, console)

        self.assertEqual(0, status)

        output = console.out.file.getvalue()
        lines = output.strip().split("\n")[1:]
        self.assertEqual(3, len(lines))
        self.assertTrue(all(i.startswith("lighthouse.") for i in lines))

    def test_help_flag(self, fixtures: Fixtures) -> None:
        cmdline = "gbp dump --help"
        console = fixtures.console

        console.out.print(f"[green]$ [/green]{cmdline}")
        with mock.patch("argparse._sys.stdout.write", console.out.print):
            with self.assertRaises(SystemExit):
                parse_args(cmdline)


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
