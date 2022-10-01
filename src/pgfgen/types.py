from __future__ import annotations

from typing import Any
from typing import Callable
from typing import TypedDict
from typing import Literal
from typing_extensions import Protocol

SearchPath = list[str]
ValueGuard = Callable[[Any], bool]

PGFGenOptionKey = Literal[
    "svg_path",
    "template_path",
]

BboxTuple = tuple[float, float, float, float]


class PGFGenOptions(TypedDict, total=False):
    svg_path: SearchPath
    template_path: SearchPath


class SupportsAppend(Protocol):
    def append(self, value: Any) -> None:
        ...
