from dataclasses import dataclass
from enum import Enum
from functools import cached_property
import hashlib
import io
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback
from typing import Any, List, Tuple
from typing import Iterator
from typing import Optional
from typing import Union

import lymbo
from lymbo.env import LYMBO_REPORT_PATH
from lymbo.env import LYMBO_TEST_SCOPE_CLASS
from lymbo.env import LYMBO_TEST_SCOPE_FUNCTION
from lymbo.env import LYMBO_TEST_SCOPE_MODULE
from lymbo.env import LYMBO_TEST_SCOPE_SESSION


class TestStatus(Enum):
    PENDING = "pending"
    INPROGRESS = "inprogress"
    PASSED = "passed"
    FAILED = "failed"
    BROKEN = "broken"
    SKIPPED = "skipped"


class ReportFailure(Enum):
    NONE = "none"
    SIMPLE = "simple"
    NORMAL = "normal"
    FULL = "full"


class GroupBy(Enum):
    NONE = "none"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"


class TestItem:
    """A test"""

    def __init__(
        self,
        path: Path,
        fnc: str,
        parameters: tuple[tuple[Any], dict[str, Any]],
        cls: Optional[str],
    ):
        self.path = path
        self.fnc = fnc
        self.parameters = parameters
        self.cls = cls

        md5 = hashlib.md5(str(self).encode()).hexdigest()
        timestamp = int(time.time() * 1000000)
        rnd = random.randint(0, 99999)
        self.uuid = f"{md5}-{timestamp}-{rnd:05d}"

        self.start_at: float = 0.0
        self.end_at: float = 0.0

        self.output: io.StringIO = io.StringIO()

        self.status: TestStatus = TestStatus.PENDING
        self.reason: str = ""
        self.error_message: List[str] = []
        self.traceback: List[str] = []

    def __str__(self):

        def print_variable(variable):
            if isinstance(variable, str):
                return f'"{variable}"'
            else:
                return str(variable)

        s = f"{self.path}::"
        if self.cls:
            s += f"{self.cls}::"
        s += f"{self.fnc}"
        args, kwargs = self.parameters
        s += "("
        call = []
        for arg in args:
            call.append(str(arg))
        for k, v in kwargs.items():
            call.append(f"{k}={print_variable(v)}")
        s += ",".join(call)
        s += ")"

        return s

    def __repr__(self) -> str:
        return f"{self.uuid}%{self}"

    def to_json(self):
        return {
            "lymbo": lymbo.__version__,
            "test": {
                "name": str(self),
                "uuid": self.uuid,
                "status": self.status.value,
                "start_at": self.start_at,
                "end_at": self.end_at,
                "output": self.output.getvalue(),
                "error": {
                    "reason": self.reason,
                    "error_message": self.error_message,
                    "traceback": self.traceback,
                },
            },
        }

    def write_report(self):

        path = f"{os.environ[LYMBO_REPORT_PATH]}/lymbo-{self.uuid}"

        with open(path + ".tmp", "w") as f:
            json.dump(self.to_json(), f, indent=4)

        os.replace(path + ".tmp", path + ".json")

    def refresh_from_report(self):

        path = f"{os.environ[LYMBO_REPORT_PATH]}/lymbo-{self.uuid}.json"

        if os.path.exists(path):

            with open(path) as f:
                test_desc = json.load(f)["test"]

                assert test_desc["uuid"] == self.uuid

                self.status = TestStatus(test_desc["status"])
                self.start_at = test_desc["start_at"]
                self.end_at = test_desc["end_at"]
                self.output = io.StringIO(test_desc["output"])
                self.reason = test_desc["error"]["reason"]
                self.error_message = test_desc["error"]["error_message"]
                self.traceback = test_desc["error"]["traceback"]

    def start(self):
        self.start_at = time.time()
        sys.stdout = self.output
        sys.stderr = self.output
        self.write_report()

    def end(self, reason: Union[Exception, None] = None):
        self.end_at = time.time()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.reason = str(reason)
        if reason is None:
            self.status = TestStatus.PASSED
        elif isinstance(reason, AssertionError):
            self.status = TestStatus.FAILED
            if not self.reason:
                self.reason = "AssertionError (no message)"
        else:
            self.status = TestStatus.BROKEN
        self.error_message = self.__error_message(reason)

        self.traceback = self.__traceback(reason)

        self.write_report()

    @property
    def duration(self):
        return self.end_at - self.start_at

    @cached_property
    def scopes(self) -> dict:
        scopes = {
            LYMBO_TEST_SCOPE_MODULE: f"{self.path}",
            LYMBO_TEST_SCOPE_SESSION: LYMBO_TEST_SCOPE_SESSION,
        }

        if self.cls:
            scopes[LYMBO_TEST_SCOPE_CLASS] = f"{self.path}::{self.cls}"
            scopes[LYMBO_TEST_SCOPE_FUNCTION] = f"{self.path}::{self.cls}::{self.fnc}"
        else:
            scopes[LYMBO_TEST_SCOPE_FUNCTION] = f"{self.path}::{self.fnc}"

        return scopes

    @staticmethod
    def __error_message(reason) -> List[str]:

        message = []

        if reason:
            tb = traceback.extract_tb(reason.__traceback__)

            # We get the line in the test where the exception has been raised
            filename, lineno, funcname, text = tb[2]

            message.append(
                f"{type(reason).__name__} in {filename}, line {lineno}, in {funcname}:"
            )

            # To have a better context, we retrieve 2 lines before the error, and 1 line after
            with open(filename, "r") as f:
                lines = f.readlines()

            start_line = max(0, lineno - 3)
            end_line = min(lineno + 1, len(lines) - 1)

            for i in range(start_line, end_line + 1):
                flag = (
                    "<====" if i == lineno - 1 else "  "
                )  # to indicate where was the error
                message.append(f"{i + 1}: {lines[i].rstrip()} {flag}")

        return message

    @staticmethod
    def __traceback(reason) -> List[str]:

        trcbck = []

        if reason:

            for lines in traceback.format_exception(
                type(reason), reason, reason.__traceback__
            )[3:]:
                for line in lines.split("\n"):
                    trcbck.append(line)

        return trcbck


@dataclass
class TestPlan:
    groups: list[list[TestItem]]
    group_by: GroupBy

    def __iter__(self) -> Iterator[list[TestItem]]:
        for group in self.groups:
            yield group

    @cached_property
    def count(self) -> tuple[int, int]:
        """Number of tests and number of groups"""
        nb_groups = len(self.groups)
        nb_tests = 0

        for group in self.groups:
            nb_tests += len(group)

        return nb_tests, nb_groups

    def __str__(self) -> str:
        test_plan, _ = self.test_plan()
        return test_plan

    def test_plan(
        self,
        show_status: bool = False,
    ) -> Tuple[str, dict[TestStatus, int]]:
        output: list[str] = []
        tests_status = {status: 0 for status in TestStatus}
        for tests in self.groups:
            if len(tests) > 1:
                group_msg = f"+ {len(tests)} tests grouped by "
                if self.group_by == GroupBy.MODULE:
                    group_msg += f"{tests[0].path}"
                if self.group_by == GroupBy.CLASS:
                    group_msg += f"{tests[0].path}::{tests[0].cls}"
                if self.group_by == GroupBy.FUNCTION:
                    group_msg += f"{tests[0].path}::{tests[0].cls}::{tests[0].fnc}"
                output.append(group_msg)
            for test in tests:
                repr = f"{'  | -' if len(tests)>1 else '-'} {test}"
                if show_status:
                    test.refresh_from_report()
                    tests_status[test.status] += 1
                    repr += f" [{test.status.value.upper()}]"
                output.append(repr)

        return "\n".join(output), tests_status

    def failures(
        self,
        report_failure: ReportFailure = ReportFailure.NORMAL,
    ) -> Tuple[str, int]:
        output: list[str] = []

        nb = 0
        for tests in self.groups:
            for test in tests:
                test.refresh_from_report()
                if test.status in (TestStatus.BROKEN, TestStatus.FAILED):
                    nb += 1
                    padding = "  "
                    output.append(str(test))
                    test_output = [line for line in test.output.getvalue().split("\n")]
                    if test_output and not test_output[-1].strip():
                        del test_output[-1]
                    if test_output:
                        output.append(" - - - - output:")
                        for line in test_output:
                            output.append(f"{padding}{line}")
                    output.append(" - - - - reason:")
                    if report_failure in (
                        ReportFailure.SIMPLE,
                        ReportFailure.NORMAL,
                        ReportFailure.FULL,
                    ):
                        output.append(f"{padding}{test.reason}")
                    if report_failure in (ReportFailure.NORMAL, ReportFailure.FULL):
                        output.append(f"{padding}---------------------")
                        for line in test.error_message:
                            not_empty_line = line.strip()
                            if not_empty_line:
                                output.append(f"{padding}{not_empty_line}")
                    if report_failure == ReportFailure.FULL:
                        output.append(f"{padding}---------------------")
                        for line in test.traceback:
                            not_empty_line = line.strip()
                            if not_empty_line:
                                output.append(f"{padding}{not_empty_line}")
        return "\n".join(output), nb
