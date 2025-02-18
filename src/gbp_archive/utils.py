"""Misc. utilities for gbp-archive"""

import datetime as dt
import io
import os
import tarfile as tar
import warnings
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from functools import singledispatch
from pathlib import Path
from typing import Any, Callable, Generator, TypeVar

from gentoo_build_publisher import fs
from gentoo_build_publisher.storage import Storage
from gentoo_build_publisher.types import TAG_SYM, Build, Content

_T = TypeVar("_T")


@singledispatch
def serializable(obj: Any) -> Any:
    """Return obj as a (JSON) serializable value"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)

    return obj


@serializable.register(dt.datetime)
@serializable.register(dt.date)
def _(value: dt.date | dt.datetime) -> str:
    return value.isoformat()


_RESOLVERS: defaultdict[type, dict[str, Callable[[Any], Any]]] = defaultdict(dict)


def decode_to(type_: type[_T], data: dict[str, Any]) -> _T:
    """Use the given data dict to initialize the given type

    Converts a JSON-compatible dict into the given type based on the registered
    converters for that type.
    """
    new_data = {}
    for key, value in data.items():
        if resolver := _RESOLVERS.get(type_, {}).get(key):
            new_value = resolver(value)
        else:
            new_value = value
        new_data[key] = new_value

    if len(new_data) == 1:
        return type_(*new_data.values())
    return type_(**new_data)


def convert_to(type_: type, field: str) -> Callable[[Any], Any]:
    """Resolve the given datatype field of the given type"""

    def decorate(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        resolvers_of_type = _RESOLVERS[type_]
        resolvers_of_type[field] = func
        return func

    return decorate


if hasattr(fs, "cd"):
    warnings.warn(
        "gentoo_build_publisher.fs now has the cd function",
        DeprecationWarning,
        stacklevel=1,
    )


@contextmanager
def cd(path: str | os.PathLike[str]) -> Generator[None, None, None]:
    """Context manager to change to the given directory"""
    orig_dir = os.getcwd()

    os.chdir(path)
    yield
    os.chdir(orig_dir)


def bytes_io_to_tarinfo(
    arcname: str, fp: io.BytesIO, mode: int = 0o0644, mtime: int | None = None
) -> tar.TarInfo:
    """Return a TarInfo given BytesIO and archive name"""
    tarinfo = tar.TarInfo(arcname)
    tarinfo.size = len(fp.getvalue())
    tarinfo.mode = mode
    tarinfo.mtime = (
        mtime if mtime is not None else int(dt.datetime.utcnow().timestamp())
    )

    return tarinfo


# These are in GBP proper but not yet released
def get_path(
    storage: Storage, build: Build, content: Content, tag: str | None = None
) -> Path:
    """Return the Path of the content type for build"""
    try:
        path = storage.get_path(build, content, tag=tag)
    except TypeError:
        if tag is None:
            return storage.get_path(build, content)

        name = f"{build.machine}{TAG_SYM}{tag}" if tag else build.machine
        return storage.root.joinpath(content.value, name)

    # If we got here, we're on a recent GBP and don't need this
    msg = "This function is obsolete. Use the GBP one"
    warnings.warn(msg, DeprecationWarning, stacklevel=1)

    return path
