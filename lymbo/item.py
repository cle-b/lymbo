from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Optional


@dataclass
class TestItem:
    """A test"""

    path: Path
    fnc: str
    args: tuple[tuple[Any], dict[str, Any]]
    cls: Optional[str]
