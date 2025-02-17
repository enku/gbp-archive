"""gbp-archive type declarations"""

from typing import Any, Callable, Literal, TypeAlias

from gentoo_build_publisher.types import Build

DumpType: TypeAlias = Literal["dump"] | Literal["restore"]
DumpPhase: TypeAlias = Literal["storage"] | Literal["records"]
DumpCallback: TypeAlias = Callable[[DumpType, DumpPhase, Build], Any]


def default_dump_callback(_type: DumpType, _phase: DumpPhase, _build: Build) -> None:
    """Default DumpCallback. A noop"""
