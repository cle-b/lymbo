from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TestItem:
    """A test"""

    path: Path
    fnc: str
    cls: Optional[str]
