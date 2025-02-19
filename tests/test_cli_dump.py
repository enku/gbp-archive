"""Tests for the cli dump subcommand"""

# pylint: disable=missing-docstring

import io
import json
import tarfile as tar
from pathlib import Path
from typing import Any, cast
from unittest import mock

from gbp_testkit import TestCase
from gbp_testkit.factories import BuildFactory
from gbp_testkit.helpers import parse_args
from gentoo_build_publisher import publisher
from gentoo_build_publisher.types import Build
from unittest_fixtures import options, requires

from gbp_archive.cli.dump import handler as dump


@requires("console", "publisher", "tmpdir")
@options(environ={"records_backend": "memory"})
class DumpTests(TestCase):
    def test_dump_all(self) -> None:
        create_builds()

        path = self.fixtures.tmpdir / "test.tar"
        cmdline = f"gbp dump {path}"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(6, len(records(path)))

    def test_given_machine(self) -> None:
        create_builds()

        path = self.fixtures.tmpdir / "test.tar"
        cmdline = f"gbp dump {path} lighthouse"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(3, len(records(path)))

    def test_given_build(self) -> None:
        builds = create_builds()
        build = builds[-1]

        path = self.fixtures.tmpdir / "test.tar"
        cmdline = f"gbp dump {path} {build}"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(1, len(records(path)))

    def test_dump_to_stdout(self) -> None:
        create_builds()

        cmdline = "gbp dump -"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

        with mock.patch("gbp_archive.cli.dump.sys.stdout") as stdout:
            stdout.buffer = io.BytesIO()
            status = dump(args, gbp, console)

        self.assertEqual(0, status)
        path = self.fixtures.tmpdir / "test.tar"

        with open(path, "wb") as fp:
            fp.write(stdout.buffer.getvalue())

        self.assertEqual(6, len(records(path)))

    def test_verbose_flag(self) -> None:
        builds = create_builds()
        builds.sort(key=lambda build: (build.machine, build.build_id))

        cmdline = "gbp dump -v -"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

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

    def test_build_id_not_found(self) -> None:
        create_builds()

        path = self.fixtures.tmpdir / "test.tar"
        cmdline = f"gbp dump {path} bogus.99"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(1, status)
        self.assertEqual("bogus.99 not found.\n", console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_machine_not_found(self) -> None:
        create_builds()

        path = self.fixtures.tmpdir / "test.tar"
        cmdline = f"gbp dump {path} bogus"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = self.fixtures.console

        status = dump(args, gbp, console)

        self.assertEqual(1, status)
        self.assertEqual("bogus not found.\n", console.err.file.getvalue())
        self.assertFalse(path.exists())


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


def create_builds() -> list[Build]:
    builds = [
        *BuildFactory.create_batch(3, machine="lighthouse"),
        *BuildFactory.create_batch(2, machine="polaris"),
        *BuildFactory.create_batch(1, machine="babette"),
    ]
    for build in builds:
        publisher.pull(build)

    return builds
