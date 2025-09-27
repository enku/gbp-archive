"""gbp-archive type declarations"""

from typing import Any, Callable, Literal, TypeAlias, TypedDict

from gentoo_build_publisher.types import Build

DumpType: TypeAlias = Literal["dump"] | Literal["restore"]
DumpPhase: TypeAlias = Literal["storage"] | Literal["records"]
DumpCallback: TypeAlias = Callable[[DumpType, DumpPhase, Build], Any]


class Metadata(TypedDict):
    """Metadata provided in a dump archive"""

    version: int

    created: str
    """Timestamp of the dump in ISO-6601 format."""

    hostname: str
    """Hostname that created the dump"""

    manifest: list[str]
    """List of stringified Builds"""


def default_dump_callback(_type: DumpType, _phase: DumpPhase, _build: Build) -> None:
    """Default DumpCallback. A noop"""
