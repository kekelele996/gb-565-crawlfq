from __future__ import annotations

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    site_domains: list[str] = Field(min_length=1)
    concurrency: int = 3
    window_s: float = 20.0
    max_sequence: int = 40
    seed: int = 7
