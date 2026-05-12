from __future__ import annotations

from collections.abc import Callable
from typing import Union

from app.providers import ModelProvider


class CapabilityError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


CapabilityResult = Union[str, list[str]]
CapabilityHandler = Callable[[dict, ModelProvider], CapabilityResult]


def _require_text(input_data: dict) -> str:
    text = input_data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise CapabilityError("INVALID_INPUT", "input.text must be a non-empty string.", {"field": "text"})
    return text


def _optional_positive_int(input_data: dict, field: str, default: int) -> int:
    value = input_data.get(field, default)
    if not isinstance(value, int) or value < 1:
        raise CapabilityError("INVALID_INPUT", f"input.{field} must be a positive integer.", {"field": field})
    return value


def text_summary(input_data: dict, provider: ModelProvider) -> str:
    text = _require_text(input_data)
    max_length = _optional_positive_int(input_data, "max_length", 120)
    return provider.summarize(text, max_length=max_length)


def keyword_extract(input_data: dict, provider: ModelProvider) -> list[str]:
    text = _require_text(input_data)
    limit = _optional_positive_int(input_data, "limit", 5)
    return provider.extract_keywords(text, limit=limit)


CAPABILITIES: dict[str, CapabilityHandler] = {
    "text_summary": text_summary,
    "keyword_extract": keyword_extract,
}


def run_capability(capability: str, input_data: dict, provider: ModelProvider) -> CapabilityResult:
    handler = CAPABILITIES.get(capability)
    if handler is None:
        raise CapabilityError(
            "CAPABILITY_NOT_FOUND",
            f"Capability '{capability}' is not supported.",
            {"capability": capability},
        )
    return handler(input_data, provider)
