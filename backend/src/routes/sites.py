"""站点与配额路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import site_controller
from src.middlewares.auth import get_current_user
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.site import SiteUpdateRequest

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("")
async def list_sites(db: Session = Depends(get_db), user: User = require_permission("sites:read")):
    return site_controller.list_sites(db)


@router.get("/{site_id}")
async def get_site(site_id: str, db: Session = Depends(get_db), user: User = require_permission("sites:read")):
    return site_controller.get_site(db, site_id)


@router.patch("/{site_id}")
async def update_site(
    request: Request,
    site_id: str,
    payload: SiteUpdateRequest,
    db: Session = Depends(get_db),
    user: User = require_permission("sites:update"),
):
    return site_controller.update_site(request, db, user, site_id, payload)
