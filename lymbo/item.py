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
from typing import Any
from typing import Iterator
from typing import Optional
from typing import Union

import lymbo
from lymbo.env import LYMBO_REPORT_PATH


class TestStatus(Enum):
    PENDING = "pending"
    INPROGRESS = "inprogress"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


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
        self.reason: Union[Exception, None] = None

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
            call.append(arg)
        for k, v in kwargs.items():
            call.append(f"{k}={print_variable(v)}")
        s += ",".join(call)
        s += ")"

        return s

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
                "reason": str(self.reason),
            },
        }

    def write_report(self):

        path = f"{os.environ[LYMBO_REPORT_PATH]}/lymbo-{self.uuid}"

        with open(path + ".tmp", "w") as f:
            json.dump(self.to_json(), f, indent=4)

        os.replace(path + ".tmp", path + ".json")

    def start(self):
        self.start_at = time.time()
        sys.stdout = self.output
        sys.stderr = self.output
        self.write_report()

    def end(self, reason: Union[Exception, None] = None):
        self.end_at = time.time()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.reason = reason
        if reason is None:
            self.status = TestStatus.PASSED
        elif isinstance(reason, AssertionError):
            self.status = TestStatus.FAILED
        else:
            self.status = TestStatus.ERROR
        self.write_report()

    @property
    def duration(self):
        return self.end_at - self.start_at


@dataclass
class TestPlan:
    groups: list[list[TestItem]]

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
