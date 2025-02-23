"""Fixtures for gbp-archive"""

# pylint: disable=missing-docstring,redefined-outer-name

import os
from pathlib import Path
from typing import Iterable, cast

from gbp_testkit.factories import BuildFactory
from gbp_testkit.fixtures import build, console, environ, publisher, settings, tmpdir
from gentoo_build_publisher.types import Build
from unittest_fixtures import FixtureContext, Fixtures, fixture


@fixture("build", "publisher", "tmpdir")
def pulled_build(fixtures: Fixtures) -> Build:
    fixtures.publisher.pull(fixtures.build)

    return cast(Build, fixtures.build)


@fixture("publisher")
def builds(
    fixtures: Fixtures, machines: Iterable[tuple[str, int]] | None = None
) -> list[Build]:
    builds_: list[Build] = []
    if machines is None:
        machines = [("lighthouse", 3), ("polaris", 2), ("babette", 1)]
    for m in machines:
        builds_.extend(BuildFactory.create_batch(m[1], machine=m[0]))
    for b in builds_:
        fixtures.publisher.pull(b)

    return builds_


@fixture("tmpdir")
def cd(fixtures: Fixtures, *, cd: Path | None = None) -> FixtureContext[Path]:
    """Changes to the given directory (tmpdir by default)"""
    cwd = cwd = os.getcwd()
    cd = cd or fixtures.tmpdir
    os.chdir(cd)
    yield cd
    os.chdir(cwd)


__all__ = (
    "build",
    "console",
    "environ",
    "publisher",
    "pulled_build",
    "settings",
    "tmpdir",
)
