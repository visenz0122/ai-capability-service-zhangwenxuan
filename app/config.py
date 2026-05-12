from __future__ import annotations

import os
from dataclasses import dataclass


def _float_from_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    model_provider: str = os.getenv("MODEL_PROVIDER", "mock")
    deepseek_api_key: str | None = os.getenv("DEEPSEEK_API_KEY") or None
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    request_timeout_seconds: float = _float_from_env("REQUEST_TIMEOUT_SECONDS", 20)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def normalized_provider(self) -> str:
        return self.model_provider.strip().lower() or "mock"


def load_settings() -> Settings:
    return Settings(
        model_provider=os.getenv("MODEL_PROVIDER", "mock"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        request_timeout_seconds=_float_from_env("REQUEST_TIMEOUT_SECONDS", 20),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
