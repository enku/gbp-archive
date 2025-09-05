"""Fixtures for gbp-archive"""

# pylint: disable=redefined-outer-name,unused-argument

import io
import os
import tarfile as tar
from pathlib import Path
from typing import Iterable, cast

import gbp_testkit.fixtures as testkit
from gbp_testkit.factories import BuildFactory
from gentoo_build_publisher.types import Build
from unittest_fixtures import FixtureContext, Fixtures, fixture


@fixture(testkit.build, testkit.publisher, testkit.tmpdir)
def pulled_build(fixtures: Fixtures) -> Build:
    """A build that has been pulled"""
    fixtures.publisher.pull(fixtures.build)

    return cast(Build, fixtures.build)


@fixture(testkit.publisher)
def builds(
    fixtures: Fixtures, machines: Iterable[tuple[str, int]] | None = None
) -> list[Build]:
    """A series of (pulled) builds"""
    builds_: list[Build] = []
    if machines is None:
        machines = [("lighthouse", 3), ("polaris", 2), ("babette", 1)]
    for m in machines:
        builds_.extend(BuildFactory.create_batch(m[1], machine=m[0]))
    for b in builds_:
        fixtures.publisher.pull(b)

    return builds_


def cd(fixtures: Fixtures, *, cd: Path = Path(".")) -> FixtureContext[Path]:
    """Changes to the given directory"""
    cwd = cwd = os.getcwd()
    os.chdir(cd)
    yield cd
    os.chdir(cwd)


@fixture(testkit.tmpdir)
def tarfile(
    fixtures: Fixtures, *, tarfile: str = "test.tar", **members: bytes
) -> tar.TarFile:
    """A tarfile in tmpdir with the given contents"""
    bytes_io = io.BytesIO()
    with tar.open(tarfile, "w", fileobj=bytes_io) as tp:
        for name, data in members.items():

            parents = name.split("/")[:-1]
            for i in range(len(parents)):
                dirpath = "/".join(parents[: i + 1])
                tarinfo = tar.TarInfo(name=dirpath)
                tarinfo.size = 0
                tarinfo.type = tar.DIRTYPE
                tp.addfile(tarinfo)

            tarinfo = tar.TarInfo(name=name)
            tarinfo.size = len(data)
            tp.addfile(tarinfo, fileobj=io.BytesIO(data))

    bytes_io.seek(0)
    return tar.open(tarfile, "r", fileobj=bytes_io)
