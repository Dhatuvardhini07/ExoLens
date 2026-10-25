from __future__ import annotations


class ExoLensError(Exception):
    """An expected, user-actionable analysis failure."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
