"""Tests for the cli dump subcommand"""

# pylint: disable=missing-docstring

import io
import json
import tarfile as tar
from pathlib import Path
from typing import Any, cast
from unittest import TestCase

import gbp_testkit.fixtures as testkit
from gbpcli.utils import EPOCH
from gentoo_build_publisher import publisher
from unittest_fixtures import Fixtures, given, where

from . import lib


@given(testkit.publisher, lib.builds, testkit.tmpdir, lib.cd, testkit.gbpcli)
@given(stdout=testkit.patch)
@where(stdout__target="gbp_archive.cli.dump.sys.stdout")
@where(argparse_stdout__target="argparse._sys.stdout")
class DumpTests(TestCase):
    def test_dump_all(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")

        status = fixtures.gbpcli(f"gbp dump -f {path}")

        self.assertEqual(0, status)
        self.assertTrue(path.exists())
        self.assertEqual(6, len(records(path)))

    def test_given_machine(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")

        status = fixtures.gbpcli(f"gbp dump -f {path} lighthouse")

        self.assertEqual(0, status)
        self.assertTrue(path.exists())
        self.assertEqual(3, len(records(path)))

    def test_given_build(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]
        path = Path("test.tar")

        status = fixtures.gbpcli(f"gbp dump -f {path} {build}")

        self.assertEqual(0, status, fixtures.console.err.file.getvalue())
        self.assertTrue(path.exists())

        self.assertEqual(1, len(records(path)))

    def test_given_build_tag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]
        publisher.publish(build)

        path = Path("test.tar")

        status = fixtures.gbpcli(f"gbp dump -f {path} {build.machine}@")

        self.assertEqual(0, status, fixtures.console.err.file.getvalue())
        self.assertTrue(path.exists())

        self.assertEqual(1, len(records(path)))

    def test_given_build_tag_does_not_exist(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        build = builds[-1]
        publisher.publish(build)

        path = Path("test.tar")
        buildspec = f"{build.machine}@bogus"

        status = fixtures.gbpcli(f"gbp dump -f {path} {buildspec}")

        self.assertEqual(1, status)
        self.assertFalse(path.exists())
        self.assertEqual(
            f"{buildspec} not found.\n", fixtures.console.err.file.getvalue()
        )

    def test_dump_to_stdout(self, fixtures: Fixtures) -> None:
        fixtures.stdout.buffer = io.BytesIO()

        status = fixtures.gbpcli("gbp dump")

        self.assertEqual(0, status)
        path = Path("test.tar")

        with path.open("wb") as fp:
            fp.write(fixtures.stdout.buffer.getvalue())

        self.assertEqual(6, len(records(path)))

    def test_verbose_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        builds.sort(key=lambda build: (build.machine, build.build_id))
        fixtures.stdout.buffer = io.BytesIO()

        status = fixtures.gbpcli("gbp dump -v")

        self.assertEqual(0, status)
        expected = (
            ""
            + "\n".join(f"dumping records for {build}" for build in builds)
            + "\n"
            + "\n".join(f"dumping storage for {build}" for build in builds)
            + "\n"
        )

        self.assertEqual(expected, fixtures.console.err.file.getvalue())

    def test_build_id_not_found(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")
        cmdline = f"gbp dump -f{path} bogus.99"

        status = fixtures.gbpcli(cmdline)

        self.assertEqual(1, status)
        self.assertEqual("bogus.99 not found.\n", fixtures.console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_machine_not_found(self, fixtures: Fixtures) -> None:
        path = Path("test.tar")

        status = fixtures.gbpcli(f"gbp dump -f {path} bogus")

        self.assertEqual(1, status)
        self.assertEqual("bogus not found.\n", fixtures.console.err.file.getvalue())
        self.assertFalse(path.exists())

    def test_newer_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds

        for build in builds[:2]:
            record = publisher.repo.build_records.get(build)
            publisher.repo.build_records.save(record, completed=EPOCH)

        path = Path("test.tar")

        status = fixtures.gbpcli(f"gbp dump -N 2025-02-22 -f{path}")

        self.assertEqual(0, status)
        self.assertTrue(path.exists())

        self.assertEqual(4, len(records(path)))

    def test_list_flag(self, fixtures: Fixtures) -> None:
        status = fixtures.gbpcli("gbp dump --list lighthouse")

        self.assertEqual(0, status)
        output = fixtures.console.out.file.getvalue()
        lines = output.strip().split("\n")[1:]
        self.assertEqual(3, len(lines))
        self.assertTrue(all(i.startswith("lighthouse.") for i in lines))

    def test_help_flag(self, fixtures: Fixtures) -> None:
        with self.assertRaises(SystemExit):
            fixtures.gbpcli("gbp dump --help")


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
