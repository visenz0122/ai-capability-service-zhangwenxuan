import pytest

from app.capabilities import CapabilityError, run_capability
from app.providers import MockProvider


def test_text_summary_rejects_non_string_text():
    with pytest.raises(CapabilityError) as exc:
        run_capability("text_summary", {"text": 123}, MockProvider())

    assert exc.value.code == "INVALID_INPUT"
    assert exc.value.details == {"field": "text"}


def test_text_summary_rejects_invalid_max_length():
    with pytest.raises(CapabilityError) as exc:
        run_capability("text_summary", {"text": "hello", "max_length": 0}, MockProvider())

    assert exc.value.code == "INVALID_INPUT"
    assert exc.value.details == {"field": "max_length"}


def test_keyword_extract_rejects_invalid_limit():
    with pytest.raises(CapabilityError) as exc:
        run_capability("keyword_extract", {"text": "hello world", "limit": "five"}, MockProvider())

    assert exc.value.code == "INVALID_INPUT"
    assert exc.value.details == {"field": "limit"}


def test_registry_rejects_unknown_capability():
    with pytest.raises(CapabilityError) as exc:
        run_capability("unknown", {"text": "hello"}, MockProvider())

    assert exc.value.code == "CAPABILITY_NOT_FOUND"
    assert exc.value.details == {"capability": "unknown"}
