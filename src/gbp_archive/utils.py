"""Misc. utilities for gbp-archive"""

import datetime as dt
import io
import tarfile as tar
from collections import defaultdict
from typing import IO, Any, Callable, TypeVar

_T = TypeVar("_T")


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


def tarfile_next(tarfile: tar.TarFile) -> tar.TarInfo:
    """Return the next member of the tarfile

    If no next member exists, raise ReadError.
    """
    if member := tarfile.next():
        return member
    raise tar.ReadError("Unexpected end of archive")


def tarfile_extract(tarfile: tar.TarFile, member: tar.TarInfo) -> IO[bytes]:
    """Extract the given member from the given tarfile

    If the member does not exist in the tarfile, raise ReadError.
    """
    if fp := tarfile.extractfile(member):
        return fp
    raise tar.ReadError(f"Member {member} does not exist in the archive")
