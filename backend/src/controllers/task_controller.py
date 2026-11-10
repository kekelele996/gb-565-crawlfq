"""任务 controller。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.task import TaskCreateRequest
from src.services import task_service


def list_tasks(db: Session) -> dict:
    return task_service.list_tasks(db)


def create_task(request: Request, db: Session, user: User, payload: TaskCreateRequest) -> dict:
    return task_service.create_task(
        db,
        payload.model_dump(),
        actor=user,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )


def get_task(db: Session, task_id: str) -> dict:
    return task_service.get_task_detail(db, task_id)


def simulate(request: Request, db: Session, user: User, task_id: str) -> dict:
    return task_service.simulate_task(
        db,
        task_id,
        actor=user,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
