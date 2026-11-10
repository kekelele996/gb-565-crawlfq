"""统一错误码（错误体：{code, message, detail, trace_id}）。"""
from __future__ import annotations

AUTH_REQUIRED = "CRF-4010"
AUTH_INVALID = "CRF-4011"
FORBIDDEN = "CRF-4030"
NOT_FOUND = "CRF-4040"
CONFLICT = "CRF-4090"
VALIDATION_ERROR = "CRF-4220"
RATE_LIMITED = "CRF-4290"
INTERNAL_ERROR = "CRF-5000"

ERROR_MESSAGES: dict[str, str] = {
    AUTH_REQUIRED: "请先登录",
    AUTH_INVALID: "邮箱或密码不正确 / 登录已过期",
    FORBIDDEN: "当前角色没有该操作权限",
    NOT_FOUND: "目标资源不存在",
    CONFLICT: "资源状态冲突",
    VALIDATION_ERROR: "参数校验失败",
    RATE_LIMITED: "请求过于频繁，请稍后重试",
    INTERNAL_ERROR: "服务内部错误",
}

HTTP_STATUS: dict[str, int] = {
    AUTH_REQUIRED: 401,
    AUTH_INVALID: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    CONFLICT: 409,
    VALIDATION_ERROR: 422,
    RATE_LIMITED: 429,
    INTERNAL_ERROR: 500,
}
