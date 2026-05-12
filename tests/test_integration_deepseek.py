import os

import pytest

from app.config import Settings
from app.providers import DeepSeekProvider


@pytest.mark.integration
def test_real_deepseek_text_summary_smoke():
    if os.getenv("RUN_REAL_MODEL_TESTS") != "1" or not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("Set RUN_REAL_MODEL_TESTS=1 and DEEPSEEK_API_KEY to run this smoke test.")

    provider = DeepSeekProvider(Settings(model_provider="deepseek"))
    result = provider.summarize(
        "Capability services should provide stable contracts, provider abstraction, tests, and graceful errors.",
        max_length=80,
    )

    assert isinstance(result, str)
    assert result.strip()
    assert len(result) <= 160
