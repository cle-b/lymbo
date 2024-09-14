import ast
import glob
import importlib
import os
from pathlib import Path
import sys
from typing import Union
from unittest.mock import patch

from lymbo.config import GroupBy
from lymbo.env import LYMBO_TEST_COLLECTION
from lymbo.item import TestItem
from lymbo.item import TestPlan
from lymbo.log import trace_call

from lymbo.cm import args


@trace_call
def list_python_files(paths: list[Path]) -> list[Path]:
    """Walk into all directories and subdirectories to list the Python files."""
    tests_files = []
    for path in paths:
        if path.is_file() and path.name.endswith(".py"):
            tests_files.append(path)
        elif path.is_dir():
            if not path.name.startswith("__"):
                for p in glob.glob(f"{path}/**"):
                    tests_files += list_python_files(
                        [
                            Path(p),
                        ]
                    )
    return list(set(tests_files))


@trace_call
def list_tests_from_file(path: Path, group_by: GroupBy) -> list[list[TestItem]]:
    """List all the tests defined in a file."""

    collected_tests = []

    with open(path) as f:
        source = f.read()

    syspath = sys.path + [
        str(path.parent.absolute()),
    ]

    with patch.object(sys, "path", syspath):

        tree = ast.parse(source, path)

        # get the context
        imports = extract_imports(tree)
        global_vars = dynamic_import_modules(
            imports
        )  # we must ensure the import are done, if the module contains a class

        local_vars: dict[str, str] = {}
        compiled_code = compile(source, path, "exec")
        exec(
            compiled_code, global_vars, local_vars
        )  # we execute the module to retrieve the global and local vars

        tests = parse_body(group_by, tree.body, path, None, global_vars, local_vars)
        if group_by == GroupBy.MODULE:
            collected_tests.append([test[0] for test in tests])
        else:
            collected_tests += tests

    return collected_tests


def parse_body(
    group_by: GroupBy,
    body: list[ast.stmt],
    path: Path,
    classdef: Union[ast.ClassDef, None],
    global_vars,
    local_vars,
) -> list[list[TestItem]]:
    """Parse the body a module/class to find test."""
    collected_tests = []
    for item in body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in item.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "test":
                            if getattr(decorator.func.value, "id", None) == "lymbo":

                                args_call = None

                                if decorator.args:
                                    args_call = decorator.args[0]
                                else:
                                    for kw in decorator.keywords:
                                        if kw.arg == "args":
                                            args_call = kw.value

                                if args_call:
                                    flattened_args = eval_ast_call(
                                        args_call, global_vars, local_vars
                                    )
                                else:
                                    flattened_args = args()

                                tests = []
                                for f_args in flattened_args:
                                    tests.append(
                                        [
                                            TestItem(
                                                path,
                                                isinstance(item, ast.AsyncFunctionDef),
                                                item.name,
                                                f_args,
                                                classdef.name if classdef else None,
                                            ),
                                        ]
                                    )
                                if (len(tests) > 1) and (group_by == GroupBy.FUNCTION):
                                    collected_tests.append([test[0] for test in tests])
                                else:
                                    # error: Argument 1 to "extend" of "list" has
                                    # incompatible type "list[list[TestItem]]"; expected
                                    # "Iterable[list[list[TestItem]]]"
                                    collected_tests.extend(tests)  # type: ignore[arg-type]
        elif isinstance(item, ast.ClassDef):
            tests = parse_body(group_by, item.body, path, item, global_vars, local_vars)
            if group_by == GroupBy.CLASS:
                collected_tests.append([test[0] for test in tests])
            else:
                # error: Argument 1 to "extend" of "list" has incompatible
                # type "list[list[TestItem]]"; expected "Iterable[list[list[TestItem]]]"
                collected_tests.extend(tests)  # type: ignore[arg-type]

    return collected_tests


@trace_call
def collect_tests(paths: list[Path], group_by: GroupBy) -> TestPlan:
    """Collect all the functions/methods decorated with @lymbo.test."""

    tests = []

    os.environ[LYMBO_TEST_COLLECTION] = "1"

    for path in list_python_files(paths):

        tests += list_tests_from_file(path, group_by)

    del os.environ[LYMBO_TEST_COLLECTION]

    test_plan = TestPlan(tests, group_by)

    return test_plan


def eval_ast_call(call_node, global_vars, local_vars):

    # local_vars and global_vars should be passed in the context
    # where the AST was created

    # Retrieve the function object
    func = eval(
        compile(ast.Expression(call_node.func), "", mode="eval"),
        global_vars,
        local_vars,
    )

    # Evaluate the arguments (handling more complex expressions, not just literals)
    args = [
        eval(compile(ast.Expression(arg), "", mode="eval"), global_vars, local_vars)
        for arg in call_node.args
    ]

    # Evaluate the keyword arguments (handling more complex expressions)
    kwargs = {
        kw.arg: eval(
            compile(ast.Expression(kw.value), "", mode="eval"), global_vars, local_vars
        )
        for kw in call_node.keywords
    }

    # Call the function with the evaluated arguments and keyword arguments
    return func(*args, **kwargs)


def set_parent_references(node: ast.AST, parent: ast.AST = None):
    """Set parent references in all nodes."""
    node.parent = parent  # type: ignore[attr-defined]
    for child in ast.iter_child_nodes(node):
        set_parent_references(child, node)


def extract_imports(tree: ast.Module) -> list[tuple[str, str]]:
    """Extracts all top-level imports from the given module and returns them
    as a list of module names or alias."""

    set_parent_references(tree)  # to detect if this is a top level import or not

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and isinstance(
            node.parent, (ast.Module, ast.ClassDef)  # type: ignore[attr-defined]
        ):
            for alias in node.names:
                imports.append(
                    (alias.name, alias.asname if alias.asname else alias.name)
                )
        elif isinstance(node, ast.ImportFrom) and isinstance(
            node.parent, (ast.Module, ast.ClassDef)  # type: ignore[attr-defined]
        ):
            module_name = node.module
            for alias in node.names:
                full_name = f"{module_name}.{alias.name}"
                imports.append(
                    (full_name, alias.asname if alias.asname else alias.name)
                )

    return imports


def dynamic_import_modules(imports: list[tuple[str, str]]) -> dict[str, str]:
    """Dynamically imports the modules and returns a dictionary of imported names."""
    global_vars = {}

    for full_name, alias in imports:
        # Import the module or specific attribute
        module_name, _, attr_name = full_name.rpartition(".")
        if module_name:  # This handles `from module import name`
            module = importlib.import_module(module_name)
            try:
                # Try to get the attribute from the module
                global_vars[alias] = getattr(module, attr_name)
            except AttributeError:
                # If it's not an attribute, treat it as a submodule and import it
                global_vars[alias] = importlib.import_module(full_name)
        else:  # This handles `import module`
            global_vars[alias] = importlib.import_module(full_name)

    return global_vars
