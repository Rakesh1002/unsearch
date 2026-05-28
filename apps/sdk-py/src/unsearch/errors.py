from __future__ import annotations

from typing import Any


class UnSearchError(Exception):
    def __init__(self, message: str, status: int, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body

    def __repr__(self) -> str:
        return f"UnSearchError(status={self.status}, message={self.args[0]!r})"
