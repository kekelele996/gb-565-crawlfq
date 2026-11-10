"""采集任务与调度模拟路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import task_controller
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.task import TaskCreateRequest

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(db: Session = Depends(get_db), user: User = require_permission("tasks:read")):
    return task_controller.list_tasks(db)


@router.post("")
async def create_task(
    request: Request,
    payload: TaskCreateRequest,
    db: Session = Depends(get_db),
    user: User = require_permission("tasks:create"),
):
    return task_controller.create_task(request, db, user, payload)


@router.get("/{task_id}")
async def get_task(task_id: str, db: Session = Depends(get_db), user: User = require_permission("tasks:read")):
    return task_controller.get_task(db, task_id)


@router.post("/{task_id}/simulate")
async def simulate(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
    user: User = require_permission("tasks:simulate"),
):
    return task_controller.simulate(request, db, user, task_id)
