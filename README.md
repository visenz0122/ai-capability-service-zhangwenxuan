# AI Capability Service

A minimal production-style backend service for unified model capability invocation. It implements the required `POST /v1/capabilities/run` API, includes deterministic local capabilities for reliable review, and can optionally call the real DeepSeek API through an OpenAI-compatible client.

## Features

- Required `text_summary` capability
- Bonus `keyword_extract` capability
- Optional real DeepSeek provider via `MODEL_PROVIDER=deepseek`
- Stable success/error response envelope
- Request ID propagation or automatic generation
- `elapsed_ms` timing in every success and failure response
- One structured log line per request with capability, provider, status, error code, and elapsed time
- Pytest coverage for API, capability validation, mock provider, and DeepSeek provider error handling
- Ruff linting and GitHub Actions CI for repeatable review

## Requirements

- Python 3.9+
- `pip`

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

Expected response:

```json
{"ok":true,"status":"healthy"}
```

## Run A Capability

### Mock text summary

The service defaults to `MODEL_PROVIDER=mock`, so it works without external accounts or API keys.

```bash
curl -s -X POST http://127.0.0.1:8000/v1/capabilities/run \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "text_summary",
    "input": {
      "text": "FastAPI makes it easy to build production-ready APIs with Python type hints.",
      "max_length": 60
    },
    "request_id": "demo-001"
  }'
```

Example response:

```json
{
  "ok": true,
  "data": {
    "result": "FastAPI makes it easy to build production-ready APIs..."
  },
  "meta": {
    "request_id": "demo-001",
    "capability": "text_summary",
    "elapsed_ms": 1
  }
}
```

### Mock keyword extraction

```bash
curl -s -X POST http://127.0.0.1:8000/v1/capabilities/run \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "keyword_extract",
    "input": {
      "text": "AI capability services need stable APIs, provider abstraction, testing, logging, and graceful error handling.",
      "limit": 5
    }
  }'
```

## DeepSeek Provider

DeepSeek support is optional and enabled only through environment variables. Do not commit real API keys.

```bash
export MODEL_PROVIDER=deepseek
export DEEPSEEK_API_KEY="your-deepseek-api-key"
export DEEPSEEK_MODEL=deepseek-v4-flash
uvicorn app.main:app --reload --port 8000
```

The provider uses:

- Base URL: `https://api.deepseek.com`
- Default model: `deepseek-v4-flash`
- Python SDK: OpenAI-compatible `openai` client

DeepSeek example:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/capabilities/run \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "text_summary",
    "input": {
      "text": "Capability services should provide stable contracts, provider abstraction, tests, logs, and graceful error handling.",
      "max_length": 80
    }
  }'
```

## Response Contract

Success:

```json
{
  "ok": true,
  "data": {
    "result": "..."
  },
  "meta": {
    "request_id": "...",
    "capability": "text_summary",
    "elapsed_ms": 12
  }
}
```

Failure:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "Human readable message",
    "details": {}
  },
  "meta": {
    "request_id": "...",
    "capability": "text_summary",
    "elapsed_ms": 12
  }
}
```

`elapsed_ms` is measured around the full request handling path for both success and failure responses.

## Error Codes

- `INVALID_REQUEST`: request body does not match the API schema
- `INVALID_INPUT`: capability input is missing or invalid
- `CAPABILITY_NOT_FOUND`: requested capability is not registered
- `PROVIDER_NOT_CONFIGURED`: selected provider is missing required configuration
- `PROVIDER_TIMEOUT`: provider request timed out
- `PROVIDER_RATE_LIMITED`: provider returned a rate limit response
- `PROVIDER_ERROR`: provider returned an unexpected error
- `INTERNAL_ERROR`: unexpected service error

## Tests

Default test suite:

```bash
source .venv/bin/activate
ruff check .
pytest -q
```

Default tests use the deterministic mock provider. The real DeepSeek smoke test is intentionally skipped unless
explicitly enabled, so reviewers can verify the project without any external credentials.

Optional real DeepSeek smoke test:

```bash
export RUN_REAL_MODEL_TESTS=1
export DEEPSEEK_API_KEY="your-deepseek-api-key"
pytest -m integration -q
```

GitHub Actions also runs `ruff check .` and `pytest -q` on every push and pull request.

## Configuration

Copy `.env.example` if you want a local reference:

```bash
cp .env.example .env
```

Environment variables:

| Name | Default | Description |
| --- | --- | --- |
| `MODEL_PROVIDER` | `mock` | `mock` or `deepseek` |
| `DEEPSEEK_API_KEY` | empty | Required only when `MODEL_PROVIDER=deepseek` |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | DeepSeek chat model |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI-compatible DeepSeek endpoint |
| `REQUEST_TIMEOUT_SECONDS` | `20` | Provider request timeout |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Notes

- The service intentionally avoids database, auth, queues, streaming, and frontend code to keep the assignment focused and runnable.
- Secrets are read only from environment variables.
- Logs never include full request input or API keys.
- DeepSeek outputs are normalized by the service before returning: summaries are clamped to the requested length and
  empty keyword responses become `PROVIDER_ERROR`.
