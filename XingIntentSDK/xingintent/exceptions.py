"""Exceptions for XingIntent SDK."""

from typing import List, Optional


class XingIntentError(Exception):
    """Base exception for all XingIntent SDK errors."""


class SchemaError(XingIntentError):
    """Raised when intent schema definition is invalid."""


class PromptError(XingIntentError):
    """Raised when prompt assembly fails."""


class APIError(XingIntentError):
    """Raised when the model API request fails."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ParseError(XingIntentError):
    """Raised when model response cannot be parsed as valid JSON."""

    def __init__(self, message: str, raw_content: str = ""):
        super().__init__(message)
        self.raw_content = raw_content


class ValidationError(XingIntentError):
    """Raised when parsed result fails schema validation."""

    def __init__(
        self,
        message: str,
        category: str = "",
        invalid_args: Optional[List[str]] = None,
    ):
        super().__init__(message)
        self.category = category
        self.invalid_args = invalid_args or []
