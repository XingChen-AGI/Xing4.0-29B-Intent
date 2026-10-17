"""Tests for SDK initialization and public API exports."""

import xingintent
from xingintent import (
    APIError,
    Arg,
    AsyncIntentClient,
    Dialog,
    Intent,
    IntentClient,
    IntentResult,
    ParseError,
    PredictResult,
    Schema,
    SchemaError,
    ValidationError,
    XingIntentError,
)


def test_all_exports():
    """All names in __all__ must be importable."""
    for name in xingintent.__all__:
        assert hasattr(xingintent, name), f"Missing export: {name}"


def test_version():
    assert hasattr(xingintent, "__version__")
    assert xingintent.__version__ == "0.1.0"


def test_exception_hierarchy():
    """All custom exceptions inherit from XingIntentError."""
    assert issubclass(SchemaError, XingIntentError)
    assert issubclass(APIError, XingIntentError)
    assert issubclass(ParseError, XingIntentError)
    assert issubclass(ValidationError, XingIntentError)


def test_api_error_has_status_code():
    err = APIError("test", status_code=503, response_body="backend down")
    assert err.status_code == 503
    assert err.response_body == "backend down"


def test_parse_error_has_raw_content():
    err = ParseError("bad json", raw_content="xxx")
    assert err.raw_content == "xxx"


def test_validation_error_has_category():
    err = ValidationError("bad category", category="foo", invalid_args=["bar"])
    assert err.category == "foo"
    assert err.invalid_args == ["bar"]
