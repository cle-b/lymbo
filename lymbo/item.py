from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any
from typing import Iterator
from typing import Optional


@dataclass
class TestItem:
    """A test"""

    path: Path
    fnc: str
    parameters: tuple[tuple[Any], dict[str, Any]]
    cls: Optional[str]

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
