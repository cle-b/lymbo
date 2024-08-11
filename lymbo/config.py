import argparse
from enum import Enum
from pathlib import Path


class GroupBy(Enum):
    NONE = "none"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(description="lymbo")

    parser.add_argument(
        "paths",
        metavar="PATH",
        type=Path,
        nargs="*",
        help="Path(s) for test collection",
    )

    parser.add_argument(
        "--version", action="store_true", help="Print the version and exit."
    )

    parser.add_argument(
        "--collect", action="store_true", help="Print the test plan and exit."
    )

    parser.add_argument(
        "--groupby",
        type=GroupBy,
        choices=list(GroupBy),
        default=GroupBy.NONE,
        help="Grouped tests are executed sequentialy",
    )

    return parser.parse_args()
