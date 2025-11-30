"""Tests for the utils.archive subpackage"""

# pylint: disable=missing-docstring

import io
import json
import tarfile as tar
from typing import Any
from unittest import TestCase, mock

import gbp_testkit.fixtures as testkit
from gentoo_build_publisher import publisher, signals
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, Param, given, where

from gbp_archive import storage
from gbp_archive.core import dump, restore

from . import lib


@given(testkit.publisher, lib.builds)
@where(builds__machines=[("foo", 3), ("bar", 2), ("baz", 1)])
class CoreDumpTests(TestCase):
    # pylint: disable=unused-argument
    def test(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        for build in builds:
            publisher.pull(build)

        outfile = io.BytesIO()
        dump(builds, outfile)
        outfile.seek(0)

        with tar.open(mode="r", fileobj=outfile) as tarfile:
            names = tarfile.getnames()
            self.assertEqual(names, ["gbp-archive", "records.json", "storage.tar"])

            metadata_fp = tarfile.extractfile("gbp-archive")
            assert metadata_fp is not None
            with metadata_fp:
                metadata = json.load(metadata_fp)
            metadata_builds = {Build.from_id(i) for i in metadata["manifest"]}
            self.assertEqual(set(builds), metadata_builds)

            fp = tarfile.extractfile("storage.tar")
            assert fp is not None
            with fp:
                with tar.open(mode="r", fileobj=fp) as storage_tarfile:
                    names = storage_tarfile.getnames()
                    self.assertEqual(126, len(names))

            records = tarfile.extractfile("records.json")
            assert records is not None
            with records:
                data = json.load(records)
                self.assertEqual(6, len(data))


@given(testkit.publisher, lib.builds)
@where(builds__machines=[("foo", 3), ("bar", 2), ("baz", 1)])
class CoreRestoreTests(TestCase):
    # pylint: disable=unused-argument
    def test(self, fixtures: Fixtures) -> None:
        builds = fixtures.builds
        for build in builds:
            publisher.pull(build)

        fp = io.BytesIO()
        dump(builds, fp)
        fp.seek(0)

        for build in builds:
            publisher.delete(build)
            self.assertFalse(publisher.storage.pulled(build))
            self.assertFalse(publisher.repo.build_records.exists(build))

        restore(fp)

        for build in builds:
            self.assertTrue(publisher.storage.pulled(build))
            self.assertTrue(publisher.repo.build_records.exists(build))

    def test_emits_pulled_signals(self, fixtures: Fixtures) -> None:
        # given the dumped builds
        builds = fixtures.builds
        fp = io.BytesIO()

        for build in builds:
            publisher.pull(build)

        dump(builds, fp)
        fp.seek(0)

        for build in builds:
            publisher.delete(build)

        # given the pre_pull and post_pull signal handlers
        pre_pull_args: list[dict[str, Any]] = []
        post_pull_args: list[dict[str, Any]] = []

        def pre_pull(**kwargs: Any) -> None:
            pre_pull_args.append(kwargs)

        def post_pull(**kwargs: Any) -> None:
            post_pull_args.append(kwargs)

        dispatcher = signals.dispatcher
        dispatcher.bind(prepull=pre_pull)
        dispatcher.bind(postpull=post_pull)

        # when we restore the builds
        restore(fp)

        # then signal handlers are called for each build
        builds = sorted(builds, key=lambda build: (build.machine, int(build.build_id)))
        build_count = len(builds)

        self.assertEqual(len(pre_pull_args), build_count)
        self.assertEqual(len(post_pull_args), build_count)

        for build, pre_args, post_args in zip(builds, pre_pull_args, post_pull_args):
            self.assertEqual(pre_args, {"build": build})

            self.assertEqual(
                post_args,
                {
                    "build": publisher.record(build),
                    "packages": publisher.storage.get_packages(build),
                    "gbp_metadata": publisher.storage.get_metadata(build),
                },
            )


@given(testkit.tmpdir, lib.cd, testkit.publisher, build=lib.pulled_build)
@where(cd=Param(lambda fixtures: fixtures.tmpdir))
class StorageDumpTestCase(TestCase):
    """Tests for Storage.dump"""

    def test(self, fixtures: Fixtures) -> None:
        """Should raise an exception if the build has not been pulled"""
        # Given the pulled build
        build = fixtures.build
        publisher.publish(build)
        publisher.tag(build, "mytag")

        # Given the storage, and file object
        path = "dump.tar"
        with open(path, "wb") as out:

            # Then we can dump the builds to the file
            start = out.tell()
            callback = mock.Mock()
            storage.dump([build], out, callback=callback)

            self.assertGreater(out.tell(), start)

        with tar.open(path) as fp:
            contents = fp.getnames()

        # And the resulting tarfile has the contents we expect
        bid = str(build)
        self.assertIn(f"repos/{bid}", contents)
        self.assertIn(f"binpkgs/{bid}", contents)
        self.assertIn(f"etc-portage/{bid}", contents)
        self.assertIn(f"var-lib-portage/{bid}", contents)
        self.assertIn(f"var-lib-portage/{build.machine}", contents)
        self.assertIn(f"var-lib-portage/{build.machine}@mytag", contents)

        # And the callback is called with the expected arguments
        callback.assert_called_once_with("dump", "storage", build)


@given(testkit.tmpdir, testkit.publisher, build=lib.pulled_build)
class StorageRestoreTests(TestCase):
    """Tests for storage.restore"""

    def test(self, fixtures: Fixtures) -> None:
        # Given the pulled build
        build = fixtures.build
        publisher.publish(build)
        publisher.tag(build, "mytag")

        # Given the dump of it
        fp = io.BytesIO()
        # storage = publisher.storage
        callback = mock.Mock()
        storage.dump([build], fp, callback=callback)

        # When we run restore on it
        publisher.delete(build)
        self.assertFalse(publisher.pulled(build))
        fp.seek(0)
        restored = storage.restore(fp, callback=callback)

        # Then we get the builds restored
        self.assertEqual([build], restored)
        self.assertTrue(publisher.storage.pulled(build))
        tags = publisher.storage.get_tags(build)
        self.assertEqual(["", "mytag"], tags)

        # And the callback is called with the expected arguments
        callback.assert_called_with("restore", "storage", build)
