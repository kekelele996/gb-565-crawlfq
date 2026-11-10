"""分页参数归一化。"""
from __future__ import annotations


def normalize_pagination(page: int | None, page_size: int | None, *, max_size: int = 200) -> tuple[int, int]:
    page = max(1, int(page or 1))
    page_size = int(page_size or 20)
    page_size = max(1, min(max_size, page_size))
    return page, page_size
