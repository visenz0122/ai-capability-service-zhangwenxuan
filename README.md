# AI Capability Service

A production-style FastAPI backend for unified AI capability invocation. The service implements the required
`POST /v1/capabilities/run` endpoint, runs locally without external credentials through a deterministic mock provider,
and can optionally call the real DeepSeek API through an OpenAI-compatible client.

## Assignment Coverage

| Requirement | Status | Implementation |
| --- | --- | --- |
| Implement at least `text_summary` | Done | `text_summary` summarizes `input.text` with optional `input.max_length` |
| Use simple mock model logic | Done | Default `MockProvider` gives deterministic local results |
| Service runs locally | Done | FastAPI app starts with `uvicorn app.main:app --reload --port 8000` |
| README includes startup instructions | Done | See Quick Start |
| README includes sample curl request | Done | See API Examples |
| Production-ready standard | Done | Typed schemas, stable envelope, provider abstraction, error mapping, logs, tests, CI |

## Bonus Coverage

| Bonus Item | Status | Implementation |
| --- | --- | --- |
| Real model API | Done | `DeepSeekProvider` calls `https://api.deepseek.com` with the OpenAI-compatible SDK |
| Second capability | Done | `keyword_extract` extracts a ranked keyword list |
| Minimal tests | Done | API, capability, provider, logging, and optional integration tests |
| Logs or timing statistics | Done | Every capability response includes `meta.elapsed_ms`; every request writes one structured log line |

## Engineering Highlights

- **Stable API contract**: every success and failure response uses the required `ok/data/error/meta` envelope.
- **Provider abstraction**: capabilities call a provider interface, so mock and DeepSeek implementations share the same
  application path.
- **Safe default behavior**: the app defaults to `MODEL_PROVIDER=mock`, so reviewers can install, run, and test it
  without any API key.
- **Real DeepSeek integration**: enabling `MODEL_PROVIDER=deepseek` and `DEEPSEEK_API_KEY` routes requests to DeepSeek
  using the OpenAI-compatible Python SDK.
- **Second capability extension**: `keyword_extract` demonstrates that new capabilities can be added through the
  registry without changing the route contract.
- **Model-output hardening**: DeepSeek summaries are clamped to the requested length after the model returns, and empty
  keyword responses are converted into a controlled `PROVIDER_ERROR`.
- **Production-style error handling**: validation, unknown capability, provider timeout, rate limit, auth, and unexpected
  errors are mapped to stable error codes without exposing tracebacks.
- **Observability**: response metadata and logs include `request_id`, `capability`, `provider`, success/failure,
  `error_code`, and `elapsed_ms`.
- **Secret hygiene**: API keys are read only from environment variables. They are not committed, logged, or stored in
  test fixtures.
- **Review-friendly quality gates**: local `ruff` and `pytest` commands are documented, and GitHub Actions runs lint and
  tests on push and pull request.

## Project Structure

```text
app/
  main.py          FastAPI app, route, response envelope, logging, exception handling
  schemas.py       Pydantic request and response models
  capabilities.py  Capability registry and input validation
  providers.py     MockProvider, DeepSeekProvider, provider errors
  config.py        Environment-based settings
tests/
  test_api.py                  API envelope, request IDs, logging
  test_capabilities.py         Capability validation and registry behavior
  test_providers.py            Mock and DeepSeek provider behavior
  test_integration_deepseek.py Optional real DeepSeek smoke test
```

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

## API Contract

Endpoint:

```http
POST /v1/capabilities/run
```

Request:

```json
{
  "capability": "text_summary",
  "input": {
    "text": "Long text content...",
    "max_length": 120
  },
  "request_id": "optional-id"
}
```

Success response:

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

Failure response:

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

## API Examples

### Mock `text_summary`

The service defaults to `MODEL_PROVIDER=mock`, so this works immediately after startup.

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

### Bonus `keyword_extract`

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

Example response:

```json
{
  "ok": true,
  "data": {
    "result": ["abstraction", "apis", "capability", "error", "graceful"]
  },
  "meta": {
    "request_id": "...",
    "capability": "keyword_extract",
    "elapsed_ms": 1
  }
}
```

### Error Path

```bash
curl -s -X POST http://127.0.0.1:8000/v1/capabilities/run \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "does_not_exist",
    "input": {
      "text": "hello"
    }
  }'
```

Example response:

```json
{
  "ok": false,
  "error": {
    "code": "CAPABILITY_NOT_FOUND",
    "message": "Capability 'does_not_exist' is not supported.",
    "details": {
      "capability": "does_not_exist"
    }
  },
  "meta": {
    "request_id": "...",
    "capability": "does_not_exist",
    "elapsed_ms": 1
  }
}
```

## DeepSeek Provider

DeepSeek is optional and enabled only through environment variables:

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
- Timeout: `REQUEST_TIMEOUT_SECONDS`, default `20`

DeepSeek request example:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/capabilities/run \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "text_summary",
    "input": {
      "text": "Capability services should provide stable contracts, provider abstraction, tests, logs, and graceful error handling.",
      "max_length": 80
    },
    "request_id": "deepseek-demo-001"
  }'
```

If `MODEL_PROVIDER=deepseek` is set without `DEEPSEEK_API_KEY`, the service still starts. The request returns a controlled
`PROVIDER_NOT_CONFIGURED` error instead of crashing at startup.

## Error Codes

- `INVALID_REQUEST`: request body does not match the API schema
- `INVALID_INPUT`: capability input is missing or invalid
- `CAPABILITY_NOT_FOUND`: requested capability is not registered
- `PROVIDER_NOT_CONFIGURED`: selected provider is missing required configuration
- `PROVIDER_TIMEOUT`: provider request timed out
- `PROVIDER_RATE_LIMITED`: provider returned a rate limit response
- `PROVIDER_ERROR`: provider returned an unexpected error
- `INTERNAL_ERROR`: unexpected service error

## Logs And Timing

Every success and failure response contains `meta.elapsed_ms`, measured around the full request handling path.

Each capability request also writes one structured log line:

```text
request_id=demo-001 capability=text_summary provider=mock ok=True error_code= elapsed_ms=0
```

The service does not log full user input or API keys.

## Tests And Quality Gates

Install dependencies first:

```bash
python -m pip install -r requirements.txt
```

Run the default review suite:

```bash
ruff check .
python -m pytest -q
```

Default tests use the deterministic mock provider. One real DeepSeek integration test is intentionally skipped unless
explicitly enabled, so reviewers can run the project without external credentials.

Run the optional real DeepSeek smoke test:

```bash
export RUN_REAL_MODEL_TESTS=1
export DEEPSEEK_API_KEY="your-deepseek-api-key"
python -m pytest -m integration -q
```

GitHub Actions runs `ruff check .` and `python -m pytest -q` on every push and pull request.

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

## Scope Decisions

This assignment focuses on the backend capability service itself. It intentionally avoids database, auth, queues,
streaming responses, frontend code, and complex plugin systems because those would increase review risk without helping
the required API contract.
