"""Restore a gbp dump"""

import argparse
import sys

from gbpcli.gbp import GBP
from gbpcli.types import Console
from gentoo_build_publisher.types import Build

import gbp_archive as archive
from gbp_archive.types import DumpPhase, DumpType

HELP = "Restore a gbp dump"


def handler(args: argparse.Namespace, _gbp: GBP, console: Console) -> int:
    """Restore a gbp dump"""

    def verbose_callback(_type: DumpType, phase: DumpPhase, build: Build) -> None:
        console.err.print(f"restoring {phase} for {build}", highlight=False)

    filename = args.file
    is_stdin = filename == "-"
    kwargs = {"callback": verbose_callback} if args.verbose else {}

    try:
        # I'm using try/finally. Leave me alone pylint!
        # pylint: disable=consider-using-with
        fp = sys.stdin.buffer if is_stdin else open(filename, "rb")
        archive.restore(fp, **kwargs)
    finally:
        if not is_stdin:
            fp.close()

    return 0


# pylint: disable=R0801
def parse_args(parser: argparse.ArgumentParser) -> None:
    """Set subcommand arguments"""
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="verbose mode: list builds restored",
    )
    parser.add_argument(
        "-f",
        "--file",
        default="-",
        help='Filename to restore builds from ("-" for standard out)',
    )
