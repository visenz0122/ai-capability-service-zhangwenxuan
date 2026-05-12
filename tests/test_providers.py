import pytest

from app.config import Settings
from app.providers import DeepSeekProvider, MockProvider, ProviderError, clean_keyword_response


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def test_mock_provider_summarizes_deterministically():
    provider = MockProvider()

    result = provider.summarize("one two three four five", max_length=12)

    assert result == "one two t..."


def test_mock_provider_extracts_keywords_deterministically():
    provider = MockProvider()

    result = provider.extract_keywords("Alpha beta alpha, stable APIs and APIs.", limit=3)

    assert result == ["alpha", "apis", "beta"]


def test_clean_keyword_response_handles_commas_and_numbering():
    result = clean_keyword_response("1. Provider abstraction\n2. stable APIs, logging, testing")

    assert result == ["provider abstraction", "stable apis", "logging", "testing"]


def test_deepseek_provider_requires_api_key():
    settings = Settings(model_provider="deepseek", deepseek_api_key=None)
    provider = DeepSeekProvider(settings)

    with pytest.raises(ProviderError) as exc:
        provider.summarize("hello world", max_length=40)

    assert exc.value.code == "PROVIDER_NOT_CONFIGURED"


def test_deepseek_provider_maps_timeout(monkeypatch):
    settings = Settings(model_provider="deepseek", deepseek_api_key="test-key")
    provider = DeepSeekProvider(settings)

    def raise_timeout(*args, **kwargs):
        import httpx

        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(provider, "_create_completion", raise_timeout)

    with pytest.raises(ProviderError) as exc:
        provider.summarize("hello world", max_length=40)

    assert exc.value.code == "PROVIDER_TIMEOUT"


def test_deepseek_provider_clamps_summary_to_requested_max_length(monkeypatch):
    settings = Settings(model_provider="deepseek", deepseek_api_key="test-key")
    provider = DeepSeekProvider(settings)

    monkeypatch.setattr(
        provider,
        "_create_completion",
        lambda *args, **kwargs: _FakeCompletion(
            "This response from the model is intentionally much longer than the requested budget."
        ),
    )

    result = provider.summarize("hello world", max_length=32)

    assert len(result) <= 32
    assert result.endswith("...")


def test_deepseek_provider_rejects_empty_keyword_parse(monkeypatch):
    settings = Settings(model_provider="deepseek", deepseek_api_key="test-key")
    provider = DeepSeekProvider(settings)

    monkeypatch.setattr(provider, "_create_completion", lambda *args, **kwargs: _FakeCompletion(" , ; \n"))

    with pytest.raises(ProviderError) as exc:
        provider.extract_keywords("hello world", limit=3)

    assert exc.value.code == "PROVIDER_ERROR"
