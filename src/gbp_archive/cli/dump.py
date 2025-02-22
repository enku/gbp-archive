"""Dump builds to a file"""

import argparse
import sys
from typing import Iterable

import dateparser  # type: ignore
from gbpcli.gbp import GBP
from gbpcli.types import Console
from gbpcli.utils import EPOCH
from gentoo_build_publisher import publisher
from gentoo_build_publisher.records import BuildRecord
from gentoo_build_publisher.types import Build

import gbp_archive as archive
from gbp_archive.types import DumpPhase, DumpType

HELP = "Dump builds to a file"


class BuildSpecLookupError(LookupError):
    """The buildspec wasn't found in the Build Records"""


def handler(args: argparse.Namespace, _gbp: GBP, console: Console) -> int:
    """Dump builds to a file"""
    try:
        builds = builds_to_dump(args.machines)
    except BuildSpecLookupError as error:
        console.err.print(f"{error.args[0]} not found.")
        return 1

    builds = {build for build in builds if build.completed > args.newer}

    if args.list:
        print_builds(builds, console)
        return 0

    def verbose_callback(_type: DumpType, phase: DumpPhase, build: Build) -> None:
        console.err.print(f"dumping {phase} for {build}", highlight=False)

    filename = args.file
    is_stdout = filename == "-"
    kwargs = {"callback": verbose_callback} if args.verbose else {}

    try:
        # I'm using try/finally. Leave me alone pylint!
        # pylint: disable=consider-using-with
        fp = sys.stdout.buffer if is_stdout else open(filename, "wb")
        archive.dump(builds, fp, **kwargs)
    finally:
        if not is_stdout:
            fp.close()

    return 0


def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument(
        "-N",
        "--newer",
        "--after-date",
        type=lambda s: dateparser.parse(s).astimezone(),
        default=EPOCH,
        help="Only dump builds newer than this date(time)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="verbose mode: list builds dumped",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-t",
        "--list",
        action="store_true",
        default=False,
        help="Don't create dump, but display what builds would be dumped",
    )
    group.add_argument(
        "-f",
        "--file",
        default="-",
        help='Filename to dump builds to ("-" for standard out)',
    )
    parser.add_argument("machines", nargs="*", help="machine(s) to dump")


def print_builds(builds: Iterable[BuildRecord], console: Console) -> None:
    """Print the given builds to Console.out"""
    for build in builds:
        console.out.print(str(build))


def builds_to_dump(buildspecs: list[str]) -> set[BuildRecord]:
    """Return the set of builds to be dumped according to the given buildspecs"""
    records = publisher.repo.build_records
    all_builds = {
        build
        for machine in records.list_machines()
        for build in records.for_machine(machine)
    }
    if not buildspecs:
        return all_builds

    to_backup: set[BuildRecord] = set()

    for buildspec in buildspecs:
        to_backup.update(builds_from_spec(buildspec, all_builds))

    return to_backup


def builds_from_spec(buildspec: str, builds: set[BuildRecord]) -> set[BuildRecord]:
    """Return the set of BuildRecords matching the given buildspec

    buildspec can be:

        - <machine> Returns all the builds for the given machine
        - <machine>.<build_id> Returns the given build

    If the given machine or build doesn't exist in the build records,
    BuildSpecLookupError is raised.
    """
    subset: set[BuildRecord] = set()
    machine, _, build_id = buildspec.partition(".")

    if build_id:
        if bs := {b for b in builds if b.machine == machine and b.build_id == build_id}:
            subset.update(bs)
        else:
            raise BuildSpecLookupError(buildspec)
    else:
        if bs := {b for b in builds if b.machine == machine}:
            subset.update(bs)
        else:
            raise BuildSpecLookupError(buildspec)
    return subset
