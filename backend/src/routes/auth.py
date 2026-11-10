"""认证路由（登录公开，其余需 Bearer）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import auth_controller
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.schemas.auth import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_controller.login(request, db, payload.email, payload.password)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return auth_controller.me(user)


@router.get("/capabilities")
async def capabilities(user: User = Depends(get_current_user)):
    return auth_controller.capabilities(user)
