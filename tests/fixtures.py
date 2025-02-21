"""Fixtures for gbp-archive"""

# pylint: disable=missing-docstring

from typing import Any, cast

from gbp_testkit.fixtures import build, console, environ, publisher, settings, tmpdir
from gentoo_build_publisher.types import Build
from unittest_fixtures import Fixtures, fixture


@fixture("build", "publisher", "tmpdir")
def pulled_build(_options: Any, fixtures: Fixtures) -> Build:
    fixtures.publisher.pull(fixtures.build)

    return cast(Build, fixtures.build)


__all__ = (
    "build",
    "console",
    "environ",
    "publisher",
    "pulled_build",
    "settings",
    "tmpdir",
)
