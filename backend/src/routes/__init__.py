"""路由总装配。"""
from fastapi import APIRouter

from src.routes import audits, auth, fetches, frontier, meta, sites, tasks

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(auth.router)
api_router.include_router(sites.router)
api_router.include_router(frontier.router)
api_router.include_router(tasks.router)
api_router.include_router(fetches.router)
api_router.include_router(audits.router)

__all__ = ["api_router"]
