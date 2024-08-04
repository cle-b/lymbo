import ast
import glob
from pathlib import Path

from lymbo.config import GroupBy
from lymbo.item import TestItem


def list_python_files(paths: list[Path]) -> list[Path]:
    """Walk into all directories and subdirectories to list the Python files."""
    tests_files = []
    for path in paths:
        if path.is_file() and str(path.name).endswith(".py"):
            tests_files.append(path)
        elif path.is_dir():
            if not str(path).startswith("__"):
                for p in glob.glob(f"{path}/**"):
                    tests_files += list_python_files(
                        [
                            Path(p),
                        ]
                    )
    return list(set(tests_files))


def list_tests_from_file(path: Path, group_by: GroupBy) -> list[list[TestItem]]:
    """List all the tests defined in a file."""

    collected_tests = []

    with open(path) as f:
        source = f.read()
        tests = parse_body(group_by, ast.parse(source).body, path)
        if group_by == GroupBy.MODULE:
            collected_tests.append([test[0] for test in tests])
        else:
            collected_tests += tests

    return collected_tests


def parse_body(
    group_by: GroupBy, body: list[ast.stmt], path: Path, classdef: ast.ClassDef = None
) -> list[list[TestItem]]:
    """Parse the body a module/class to find test."""
    collected_tests = []
    for item in body:
        if isinstance(item, ast.FunctionDef):
            for decorator in item.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "test":
                            if getattr(decorator.func.value, "id", None) == "lymbo":
                                collected_tests.append(
                                    [
                                        TestItem(
                                            path,
                                            item.name,
                                            classdef.name if classdef else None,
                                        ),
                                    ]
                                )
        elif isinstance(item, ast.ClassDef):
            tests = parse_body(group_by, item.body, path, item)
            if group_by == GroupBy.CLASS:
                collected_tests.append([test[0] for test in tests])
            else:
                collected_tests += tests

    return collected_tests


def collect_tests(paths: list[Path], group_by: GroupBy) -> list[list[TestItem]]:
    """Collect all the functions/methods decorated with @lymbo.test."""

    tests = []

    for path in list_python_files(paths):

        tests += list_tests_from_file(path, group_by)

    return tests
