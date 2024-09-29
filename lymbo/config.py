import argparse
from pathlib import Path

from lymbo.item import GroupBy
from lymbo.item import ReportFailure
from lymbo.log import LogLevel


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="A test runner designed for large test suites."
    )

    parser.add_argument(
        "paths",
        metavar="PATH",
        type=Path,
        nargs="*",
        default=[Path("test", Path("tests"))],
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
        choices=GroupBy,
        default=GroupBy.NONE,
        help="Grouped tests are executed sequentialy.",
    )

    parser.add_argument(
        "--report", type=Path, help="Save the report in that directory."
    )

    parser.add_argument(
        "--log-level",
        type=LogLevel,
        choices=LogLevel,
        default=LogLevel.WARNING,
        help="The log level",
    )

    parser.add_argument("--log", type=Path, help="Path to the log file.")

    parser.add_argument(
        "--report-failure",
        type=ReportFailure,
        choices=ReportFailure,
        default=ReportFailure.NORMAL,
        help="The level of detail to display in the console in case of a failure.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="The number of workers in parrallel (default = number of CPU).",
    )

    parser.add_argument(
        "--filter",
        type=str,
        default="",
        help="Select only the tests that match this filter (include full path and parameters).",
    )

    return parser.parse_args()
