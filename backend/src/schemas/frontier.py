from __future__ import annotations

from pydantic import BaseModel, Field


class FrontierPreviewRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
