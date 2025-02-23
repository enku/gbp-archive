"""Tests for the utils.archive subpackage"""

# pylint: disable=missing-docstring

import io
import json
import tarfile as tar
from unittest import TestCase, mock

from gbp_testkit.factories import BuildFactory
from gentoo_build_publisher import publisher
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, given

import gbp_archive as archive


@given("publisher")
class CoreDumpTests(TestCase):
    # pylint: disable=unused-argument
    def test(self, fixtures: Fixtures) -> None:
        builds = [
            *BuildFactory.create_batch(3, machine="foo"),
            *BuildFactory.create_batch(2, machine="bar"),
            *BuildFactory.create_batch(1, machine="baz"),
        ]
        for build in builds:
            publisher.pull(build)

        outfile = io.BytesIO()
        archive.dump(builds, outfile)
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

            storage = tarfile.extractfile("storage.tar")
            assert storage is not None
            with storage:
                with tar.open(mode="r", fileobj=storage) as storage_tarfile:
                    names = storage_tarfile.getnames()
                    self.assertEqual(120, len(names))

            records = tarfile.extractfile("records.json")
            assert records is not None
            with records:
                data = json.load(records)
                self.assertEqual(6, len(data))


@given("publisher")
class CoreRestoreTests(TestCase):
    # pylint: disable=unused-argument
    def test(self, fixtures: Fixtures) -> None:
        builds = [
            *BuildFactory.create_batch(3, machine="foo"),
            *BuildFactory.create_batch(2, machine="bar"),
            *BuildFactory.create_batch(1, machine="baz"),
        ]
        for build in builds:
            publisher.pull(build)

        fp = io.BytesIO()
        archive.dump(builds, fp)
        fp.seek(0)

        for build in builds:
            publisher.delete(build)
            self.assertFalse(publisher.storage.pulled(build))
            self.assertFalse(publisher.repo.build_records.exists(build))

        archive.restore(fp)

        for build in builds:
            self.assertTrue(publisher.storage.pulled(build))
            self.assertTrue(publisher.repo.build_records.exists(build))


@given("cd", "tmpdir", "publisher", build="pulled_build")
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
            archive.storage.dump([build], out, callback=callback)

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


@given("tmpdir", "publisher", build="pulled_build")
class StorageRestoreTests(TestCase):
    """Tests for storage.restore"""

    def test(self, fixtures: Fixtures) -> None:
        # Given the pulled build
        build = fixtures.build
        publisher.publish(build)
        publisher.tag(build, "mytag")

        # Given the dump of it
        fp = io.BytesIO()
        storage = publisher.storage
        callback = mock.Mock()
        archive.storage.dump([build], fp, callback=callback)

        # When we run restore on it
        storage.delete(build)
        self.assertFalse(storage.pulled(build))
        fp.seek(0)
        restored = archive.storage.restore(fp, callback=callback)

        # Then we get the builds restored
        self.assertEqual([build], restored)
        self.assertTrue(storage.pulled(build))
        tags = storage.get_tags(build)
        self.assertEqual(["", "mytag"], tags)

        # And the callback is called with the expected arguments
        callback.assert_called_with("restore", "storage", build)
