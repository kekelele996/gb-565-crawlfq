"""crawlfq backend 入口：uvicorn src.main:app。"""
from __future__ import annotations

from src.config.app import app  # noqa: F401 - uvicorn 从这里加载

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
