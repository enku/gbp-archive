"""Core functions for gbp-archive"""

import tarfile as tar
import tempfile
from typing import IO, Iterable

from gentoo_build_publisher.types import Build

from gbp_archive import metadata, records, storage
from gbp_archive.types import DumpCallback, default_dump_callback
from gbp_archive.utils import tarfile_extract, tarfile_next


def dump(
    builds: Iterable[Build],
    outfile: IO[bytes],
    *,
    callback: DumpCallback = default_dump_callback,
) -> None:
    """Dump the given builds to the given outfile"""
    builds = sorted(builds, key=lambda build: (build.machine, int(build.build_id)))

    with tar.open(fileobj=outfile, mode="w|") as tarfile:
        for item in metadata, records, storage:
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
        for item in metadata, records, storage:
            fp = tarfile_extract(tarfile, tarfile_next(tarfile))
            item.restore(fp, callback=callback)
