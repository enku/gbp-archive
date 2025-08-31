"""Tests for the cli restore subcommand"""

# pylint: disable=missing-docstring

import argparse
import io
from pathlib import Path
from typing import Iterable
from unittest import TestCase, mock

import gbp_testkit.fixtures as testkit
from gbp_testkit.helpers import parse_args, print_command
from gbpcli.types import Console
from gentoo_build_publisher import publisher
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, given, where

import gbp_archive.core as archive
from gbp_archive.cli.restore import handler

from . import lib


@given(lib.builds, testkit.console, testkit.publisher, lib.cd)
@given(stdin=testkit.patch)
@where(stdin__target="gbp_archive.cli.restore.sys.stdin")
@given(argparse_stdout=testkit.patch)
@where(argparse_stdout__target="argparse._sys.stdout")
class RestoreTests(TestCase):
    def test_restore_all(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        first_build = builds[0]
        publisher.publish(first_build)
        last_build = builds[-1]
        publisher.tag(last_build, "last")
        path = Path("test.tar")
        dump_builds(builds, path)
        delete_builds(builds)

        cmdline = f"gbp restore -vf {path}"
        args = parse_args(cmdline)
        console = fixtures.console
        print_command(cmdline, console)

        status = restore(args, console)

        self.assertEqual(0, status)

        for build in builds:
            self.assertTrue(publisher.storage.pulled(build))
            self.assertTrue(publisher.repo.build_records.exists(build))

        self.assertTrue(publisher.published(first_build))
        self.assertEqual(["last"], publisher.tags(last_build))

    def test_restore_from_stdin(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        restore_image = fixtures.stdin.buffer = io.BytesIO()
        archive.dump(builds, restore_image)
        delete_builds(builds)
        restore_image.seek(0)

        cmdline = "gbp restore"
        args = parse_args(cmdline)
        console = fixtures.console

        status = restore(args, console)

        self.assertEqual(0, status)

        for build in builds:
            self.assertTrue(publisher.storage.pulled(build))
            self.assertTrue(publisher.repo.build_records.exists(build))

    def test_verbose_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        builds.sort(key=lambda build: (build.machine, int(build.build_id)))
        restore_image = fixtures.stdin.buffer = io.BytesIO()
        archive.dump(builds, restore_image)
        delete_builds(builds)
        restore_image.seek(0)

        cmdline = "gbp restore -v"
        args = parse_args(cmdline)
        console = fixtures.console

        status = restore(args, console)

        self.assertEqual(0, status)
        expected = (
            ""
            + "\n".join(f"restoring records for {build}" for build in builds)
            + "\n"
            + "\n".join(f"restoring storage for {build}" for build in builds)
            + "\n"
        )

        self.assertEqual(expected, console.err.file.getvalue())

    def test_list_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        path = Path("test.tar")
        dump_builds(builds, path)
        delete_builds(builds)

        cmdline = f"gbp restore -tf {path}"
        args = parse_args(cmdline)
        console = fixtures.console
        print_command(cmdline, console)

        status = restore(args, console)

        self.assertEqual(0, status)
        self.assertEqual(0, publisher.repo.build_records.count())

        output = console.out.file.getvalue()
        lines = output.strip().split("\n")[1:]
        self.assertEqual(len(builds), len(lines))

        for build in builds:
            self.assertIn(str(build), lines)

    def test_help_flag(self, fixtures: Fixtures) -> None:
        # pylint: disable=duplicate-code
        cmdline = "gbp restore --help"
        console = fixtures.console
        fixtures.argparse_stdout.write = console.out.print

        console.out.print(f"[green]$ [/green]{cmdline}")
        with self.assertRaises(SystemExit):
            parse_args(cmdline)


def restore(args: argparse.Namespace, console: Console) -> int:
    """Call the restore handler with a mock gbp instance"""
    return handler(args, mock.Mock(), console)


def dump_builds(builds: Iterable[Build], path: Path) -> None:
    with path.open("wb") as outfile:
        archive.dump(builds, outfile)


def delete_builds(builds: Iterable[Build]) -> None:
    for build in builds:
        publisher.delete(build)
