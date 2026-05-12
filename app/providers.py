from __future__ import annotations

import re
from typing import Protocol

import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.config import Settings


class ProviderError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class ModelProvider(Protocol):
    name: str
    model: str

    def summarize(self, text: str, max_length: int) -> str:
        ...

    def extract_keywords(self, text: str, limit: int) -> list[str]:
        ...


STOPWORDS = {
    "a",
    "an",
    "and",
    "ai",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "need",
    "needs",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def compact_summary(text: str, max_length: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized

    cutoff = max(1, max_length - 3)
    candidate = normalized[:cutoff].rstrip()
    last_space = candidate.rfind(" ")
    if last_space >= int(max_length * 0.75):
        candidate = candidate[:last_space].rstrip()
    return f"{candidate}..."


def extract_keywords_by_frequency(text: str, limit: int) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text.lower())
    counts: dict[str, int] = {}
    for word in words:
        if len(word) < 2 or word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _count in ranked[:limit]]


def clean_keyword_response(raw: str) -> list[str]:
    text = re.sub(r"(?m)^\s*\d+[\).\s-]+", "", raw.strip())
    parts = re.split(r"[,\n;]+", text)
    cleaned: list[str] = []
    for part in parts:
        value = re.sub(r"\s+", " ", part).strip(" .:-").lower()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


class MockProvider:
    name = "mock"
    model = "deterministic-local"

    def summarize(self, text: str, max_length: int) -> str:
        return compact_summary(text, max_length)

    def extract_keywords(self, text: str, limit: int) -> list[str]:
        return extract_keywords_by_frequency(text, limit)


class DeepSeekProvider:
    name = "deepseek"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.deepseek_model

    def summarize(self, text: str, max_length: int) -> str:
        if not self.settings.deepseek_api_key:
            raise ProviderError(
                "PROVIDER_NOT_CONFIGURED",
                "DEEPSEEK_API_KEY is required when MODEL_PROVIDER=deepseek.",
            )

        content = self._chat(
            system_prompt=(
                "You summarize text for an API capability service. "
                "Return only the summary text. Do not include explanations."
            ),
            user_prompt=(
                f"Summarize the following text in no more than {max_length} characters. "
                f"Text:\n{text}"
            ),
            max_tokens=160,
        )
        return content.strip()

    def extract_keywords(self, text: str, limit: int) -> list[str]:
        if not self.settings.deepseek_api_key:
            raise ProviderError(
                "PROVIDER_NOT_CONFIGURED",
                "DEEPSEEK_API_KEY is required when MODEL_PROVIDER=deepseek.",
            )

        content = self._chat(
            system_prompt=(
                "Extract keywords for an API capability service. "
                "Return only comma-separated keywords. Do not include explanations."
            ),
            user_prompt=f"Extract up to {limit} keywords from this text:\n{text}",
            max_tokens=120,
        )
        return clean_keyword_response(content)[:limit]

    def _chat(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        try:
            response = self._create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if not content:
                raise ProviderError("PROVIDER_ERROR", "DeepSeek returned an empty response.")
            return content
        except ProviderError:
            raise
        except (APITimeoutError, httpx.TimeoutException):
            raise ProviderError("PROVIDER_TIMEOUT", "DeepSeek request timed out.")
        except APIStatusError as exc:
            if exc.status_code == 429:
                raise ProviderError("PROVIDER_RATE_LIMITED", "DeepSeek rate limit exceeded.")
            if exc.status_code in {401, 403}:
                raise ProviderError("PROVIDER_ERROR", "DeepSeek authentication failed.")
            raise ProviderError(
                "PROVIDER_ERROR",
                "DeepSeek API returned an error.",
                {"status_code": exc.status_code},
            )
        except APIConnectionError:
            raise ProviderError("PROVIDER_ERROR", "Could not connect to DeepSeek API.")
        except Exception as exc:
            raise ProviderError("PROVIDER_ERROR", "DeepSeek provider failed.", {"type": type(exc).__name__})

    def _create_completion(self, messages: list[dict[str, str]], max_tokens: int):
        client = OpenAI(
            api_key=self.settings.deepseek_api_key,
            base_url=self.settings.deepseek_base_url,
            timeout=self.settings.request_timeout_seconds,
        )
        return client.chat.completions.create(
            model=self.settings.deepseek_model,
            messages=messages,
            max_tokens=max_tokens,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )


def get_provider(settings: Settings) -> ModelProvider:
    provider_name = settings.normalized_provider()
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "deepseek":
        return DeepSeekProvider(settings)
    raise ProviderError(
        "PROVIDER_NOT_CONFIGURED",
        f"Unsupported MODEL_PROVIDER '{settings.model_provider}'.",
        {"provider": settings.model_provider},
    )
