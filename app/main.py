from __future__ import annotations

import logging
import time
from typing import Union
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.capabilities import CapabilityError, run_capability
from app.config import load_settings
from app.providers import ProviderError, get_provider
from app.schemas import (
    CapabilityRunRequest,
    ErrorBody,
    ErrorResponse,
    HealthResponse,
    ResponseMeta,
    SuccessData,
    SuccessResponse,
)


settings = load_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(message)s")
logger = logging.getLogger("capability-service")

app = FastAPI(
    title="AI Capability Service",
    description="A minimal production-style backend for unified model capability invocation.",
    version="1.0.0",
)


def _elapsed_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))


def _meta(request_id: str, capability: str, start: float) -> ResponseMeta:
    return ResponseMeta(request_id=request_id, capability=capability, elapsed_ms=_elapsed_ms(start))


def _log_request(
    *,
    request_id: str,
    capability: str,
    provider: str,
    ok: bool,
    elapsed_ms: int,
    error_code: str | None = None,
) -> None:
    logger.info(
        "request_id=%s capability=%s provider=%s ok=%s error_code=%s elapsed_ms=%s",
        request_id,
        capability,
        provider,
        ok,
        error_code or "",
        elapsed_ms,
    )


def _error_response(
    *,
    code: str,
    message: str,
    details: dict,
    request_id: str,
    capability: str,
    start: float,
    provider: str,
) -> JSONResponse:
    meta = _meta(request_id, capability, start)
    _log_request(
        request_id=request_id,
        capability=capability,
        provider=provider,
        ok=False,
        error_code=code,
        elapsed_ms=meta.elapsed_ms,
    )
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details),
        meta=meta,
    )
    return JSONResponse(status_code=200, content=body.model_dump())


def _safe_validation_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    for error in exc.errors():
        errors.append(
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "Invalid request."),
                "type": error.get("type", "value_error"),
            }
        )
    return errors


@app.get("/health", response_model=HealthResponse)
def health() -> dict[str, str | bool]:
    return {"ok": True, "status": "healthy"}


@app.post("/v1/capabilities/run", response_model=Union[SuccessResponse, ErrorResponse])
def run(request_body: CapabilityRunRequest) -> JSONResponse:
    start = time.perf_counter()
    request_id = request_body.request_id or str(uuid4())
    capability = request_body.capability
    settings = load_settings()
    provider_name = settings.normalized_provider()

    try:
        provider = get_provider(settings)
        result = run_capability(capability, request_body.input, provider)
        meta = _meta(request_id, capability, start)
        _log_request(
            request_id=request_id,
            capability=capability,
            provider=provider.name,
            ok=True,
            elapsed_ms=meta.elapsed_ms,
        )
        body = SuccessResponse(data=SuccessData(result=result), meta=meta)
        return JSONResponse(status_code=200, content=body.model_dump())
    except CapabilityError as exc:
        return _error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
            capability=capability,
            start=start,
            provider=provider_name,
        )
    except ProviderError as exc:
        return _error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
            capability=capability,
            start=start,
            provider=provider_name,
        )
    except Exception:
        logger.exception("Unhandled capability service error")
        return _error_response(
            code="INTERNAL_ERROR",
            message="Unexpected service error.",
            details={},
            request_id=request_id,
            capability=capability,
            start=start,
            provider=provider_name,
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    start = time.perf_counter()
    request_id = str(uuid4())
    capability = ""
    details = {"errors": _safe_validation_errors(exc)}

    try:
        payload = await request.json()
        if isinstance(payload, dict):
            request_id = payload.get("request_id") or request_id
            raw_capability = payload.get("capability")
            capability = raw_capability if isinstance(raw_capability, str) else ""
    except Exception:
        pass

    return _error_response(
        code="INVALID_REQUEST",
        message="Request body does not match the required schema.",
        details=details,
        request_id=request_id,
        capability=capability,
        start=start,
        provider=load_settings().normalized_provider(),
    )
