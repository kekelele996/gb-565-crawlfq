"""通用 schema：统一错误体 / 分页 envelope。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: str = ""
    trace_id: str | None = None


class PageQuery(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)


class Envelope(BaseModel):
    data: Any
