from __future__ import annotations

from typing import Optional


class InvalidPath(Exception):
    """Raised when malformed filesystem path is provided to a function"""

    def __init__(self, path: Optional[str] = None, message: Optional[str] = None):
        self.path = path
        if message is None:
            message = path
        self.message = message

    def __str__(self) -> str:
        return str(self.message)


class SvgFileNotFound(FileNotFoundError):
    pass
