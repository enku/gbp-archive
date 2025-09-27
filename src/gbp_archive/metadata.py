"""Utilities for dumping dump metadata"""

import datetime as dt
import json
from typing import IO, Any, Iterable, cast

from gentoo_build_publisher.types import Build
from gentoo_build_publisher.utils import get_hostname, time

from gbp_archive.types import Metadata

ARCHIVE_NAME = "gbp-archive"


def dump(
    builds: Iterable[Build],
    fp: IO[bytes],
    *,
    callback: Any,  # pylint: disable=unused-argument
) -> None:
    """Write the given metadata to the given file"""
    metadata = create(builds, timestamp=time.localtime())
    fp.write(json.dumps(metadata).encode("utf8"))


def restore(
    infile: IO[bytes], *, callback: Any  # pylint: disable=unused-argument
) -> Metadata:
    """Return the Metadata from the given file"""
    return cast(Metadata, json.load(infile))


def create(builds: Iterable[Build], timestamp: dt.datetime) -> Metadata:
    """Return metadata dict"""
    return {
        "version": 1,
        "created": timestamp.isoformat(),
        "hostname": get_hostname(),
        "manifest": [str(build) for build in builds],
    }
