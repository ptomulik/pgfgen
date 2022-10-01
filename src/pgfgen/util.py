from __future__ import annotations

import os
import os.path
import posixpath

from .exceptions import InvalidPath
from .types import SearchPath

from typing import Callable
from typing import Optional


def split_sanitize_path(path: str) -> list[str]:
    """Split a path into segments and perform sanity check. Empty segments are
    removed. Absolute paths are actually converted to relative."""
    pieces = []
    for piece in path.split("/"):
        if (
            os.sep in piece
            or (os.path.altsep and os.path.altsep in piece)
            or piece == os.path.pardir
        ):
            raise InvalidPath(path)
        elif piece and piece != ".":
            pieces.append(piece)
    return pieces


def find_in_search_path(
    search_path: SearchPath,
    path: str,
    predicate: Callable[[str], bool] = os.path.isfile,
) -> Optional[str]:
    pieces = split_sanitize_path(path)

    for base in search_path:
        filename = posixpath.join(base, *pieces)

        if predicate(filename):
            return filename
    return None
