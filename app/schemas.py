from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CapabilityRunRequest(BaseModel):
    capability: str = Field(..., min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None


class ResponseMeta(BaseModel):
    request_id: str
    capability: str
    elapsed_ms: int


class SuccessData(BaseModel):
    result: Any


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SuccessResponse(BaseModel):
    ok: bool = True
    data: SuccessData
    meta: ResponseMeta


class ErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorBody
    meta: ResponseMeta


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ok": True, "status": "healthy"}})

    ok: bool
    status: str
