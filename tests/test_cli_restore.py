"""Tests for the cli restore subcommand"""

# pylint: disable=missing-docstring

import io
from pathlib import Path
from typing import Iterable
from unittest import TestCase, mock

from gbp_testkit.helpers import parse_args
from gentoo_build_publisher import publisher
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, given

import gbp_archive as archive
from gbp_archive.cli.restore import handler as restore


@given("builds", "console", "publisher", "tmpdir")
class RestoreTests(TestCase):
    def test_restore_all(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        first_build = builds[0]
        publisher.publish(first_build)
        last_build = builds[-1]
        publisher.tag(last_build, "last")
        path = fixtures.tmpdir / "test.tar"
        dump_builds(builds, path)
        delete_builds(builds)

        path = fixtures.tmpdir / "test.tar"
        cmdline = f"gbp restore -f{path}"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        status = restore(args, gbp, console)

        self.assertEqual(0, status)

        for build in builds:
            self.assertTrue(publisher.storage.pulled(build))
            self.assertTrue(publisher.repo.build_records.exists(build))

        self.assertTrue(publisher.published(first_build))
        self.assertEqual(["last"], publisher.tags(last_build))

    def test_restore_from_stdin(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        restore_image = io.BytesIO()
        archive.dump(builds, restore_image)
        delete_builds(builds)
        restore_image.seek(0)

        cmdline = "gbp restore"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        with mock.patch("gbp_archive.cli.restore.sys.stdin") as stdin:
            stdin.buffer = restore_image
            status = restore(args, gbp, console)

        self.assertEqual(0, status)

        for build in builds:
            self.assertTrue(publisher.storage.pulled(build))
            self.assertTrue(publisher.repo.build_records.exists(build))

    def test_verbose_flag(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        builds.sort(key=lambda build: (build.machine, build.build_id))
        restore_image = io.BytesIO()
        archive.dump(builds, restore_image)
        delete_builds(builds)
        restore_image.seek(0)

        cmdline = "gbp restore -v"

        args = parse_args(cmdline)
        gbp = mock.Mock()
        console = fixtures.console

        with mock.patch("gbp_archive.cli.restore.sys.stdin") as stdin:
            stdin.buffer = restore_image
            status = restore(args, gbp, console)

        self.assertEqual(0, status)
        expected = (
            ""
            + "\n".join(f"restoring records for {build}" for build in builds)
            + "\n"
            + "\n".join(f"restoring storage for {build}" for build in builds)
            + "\n"
        )

        self.assertEqual(expected, console.err.file.getvalue())

    def test_help_flag(self, fixtures: Fixtures) -> None:
        # pylint: disable=duplicate-code
        cmdline = "gbp restore --help"
        console = fixtures.console

        console.out.print(f"[green]$ [/green]{cmdline}")
        with mock.patch("argparse._sys.stdout.write", console.out.print):
            with self.assertRaises(SystemExit):
                parse_args(cmdline)


def dump_builds(builds: Iterable[Build], path: Path) -> None:
    with path.open("wb") as outfile:
        archive.dump(builds, outfile)


def delete_builds(builds: Iterable[Build]) -> None:
    for build in builds:
        publisher.delete(build)
