"""Core functions for gbp-archive"""

import tarfile as tar
import tempfile
from typing import IO, Iterable

from gentoo_build_publisher import publisher, signals
from gentoo_build_publisher.types import Build

from gbp_archive import metadata, records, storage
from gbp_archive.types import DumpCallback, default_dump_callback
from gbp_archive.utils import tarfile_extract, tarfile_next

ARCHIVE_ITEMS = (metadata, records, storage)


def dump(
    builds: Iterable[Build],
    outfile: IO[bytes],
    *,
    callback: DumpCallback = default_dump_callback,
) -> None:
    """Dump the given builds to the given outfile"""
    builds = sorted(builds, key=lambda build: (build.machine, int(build.build_id)))

    with tar.open(fileobj=outfile, mode="w|") as tarfile:
        for item in ARCHIVE_ITEMS:
            with tempfile.TemporaryFile(mode="w+b") as fp:
                item.dump(builds, fp, callback=callback)
                fp.seek(0)
                tarinfo = tarfile.gettarinfo(arcname=item.ARCHIVE_NAME, fileobj=fp)
                tarfile.addfile(tarinfo, fp)


def tabulate(infile: IO[bytes]) -> list[Build]:
    """Return the list of builds in the archive"""
    with tar.open(fileobj=infile, mode="r|") as tarfile:
        fp = tarfile_extract(tarfile, tarfile_next(tarfile))
        m = metadata.restore(fp, callback=None)
    return [Build.from_id(i) for i in m["manifest"]]


def restore(
    infile: IO[bytes], *, callback: DumpCallback = default_dump_callback
) -> None:
    """Restore builds from the given infile"""
    with tar.open(fileobj=infile, mode="r|") as tarfile:
        fp = tarfile_extract(tarfile, tarfile_next(tarfile))
        manifest = metadata.restore(fp, callback=callback)["manifest"]
        builds = [Build.from_id(build_str) for build_str in manifest]

        emit_prepull_signals(builds)

        fp = tarfile_extract(tarfile, tarfile_next(tarfile))
        records.restore(fp, callback=callback)

        fp = tarfile_extract(tarfile, tarfile_next(tarfile))
        storage.restore(fp, callback=callback)

        emit_postpull_signals(builds)


def emit_prepull_signals(builds: Iterable[Build]) -> None:
    """Emit prepull signals for the given builds"""
    dispatcher = signals.dispatcher

    for build in builds:
        dispatcher.emit("prepull", build=build)


def emit_postpull_signals(builds: Iterable[Build]) -> None:
    """Emit postpull signals for the given builds"""
    dispatcher = signals.dispatcher

    for build in builds:
        dispatcher.emit(
            "postpull",
            build=publisher.record(build),
            packages=publisher.storage.get_packages(build),
            gbp_metadata=publisher.storage.get_metadata(build),
        )
