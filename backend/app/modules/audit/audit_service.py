"""Write audit/action logs in their OWN session (survives business rollback),
plus query + retention helpers. Writing must never break the calling API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Query, Session

from app.core.config import settings
from app.core.database import db_session
from app.core.logger import get_context, get_logger
from app.core.request_meta import get_request_meta
from app.modules.audit.audit_model import ActionLog, AuditLog
from app.modules.audit.audit_schema import ActionLogListResponse, AuditLogListResponse
from app.modules.audit.device_service import resolve_device

logger = get_logger("wms.audit")

EVENT_LOGIN = "LOGIN"
EVENT_LOGOUT = "LOGOUT"
EVENT_PERMISSION_DENIED = "PERMISSION_DENIED"
EVENT_TOKEN_INVALID = "TOKEN_INVALID"
RESULT_SUCCESS = "SUCCESS"
RESULT_FAILED = "FAILED"


def _device_fields(db: Session, ip: Optional[str], client_type: Optional[str]) -> dict[str, Any]:
    device = resolve_device(db, ip)
    if device:
        return {"device_name": device[0], "device_type": device[1]}
    return {"device_name": None, "device_type": client_type}


def record_audit(
    event_type: str,
    result: str,
    *,
    username: Optional[str] = None,
    user_id: Optional[int] = None,
    failure_reason: Optional[str] = None,
) -> None:
    meta = get_request_meta()
    ctx = get_context()
    name = username or ctx.get("user")
    try:
        with db_session() as db:
            db.add(AuditLog(
                event_type=event_type,
                result=result,
                failure_reason=failure_reason,
                user_id=user_id if user_id is not None else ctx.get("user_id"),
                username=str(name)[:50] if name else None,
                ip=meta.get("ip"),
                user_agent=meta.get("user_agent"),
                request_id=meta.get("request_id"),
                path=(meta.get("path") or "")[:255] or None,
                **_device_fields(db, meta.get("ip"), meta.get("client_type")),
            ))
            db.commit()
    except Exception:
        logger.warning("Failed to write audit log (%s/%s)", event_type, result, exc_info=True)


def record_action(entry: dict[str, Any]) -> None:
    """``entry`` holds ActionLog columns except device fields (resolved here from ``ip``)."""
    client_type = entry.pop("client_type", None)
    try:
        with db_session() as db:
            db.add(ActionLog(**entry, **_device_fields(db, entry.get("ip"), client_type)))
            db.commit()
    except Exception:
        logger.warning("Failed to write action log for %s %s", entry.get("method"), entry.get("path"), exc_info=True)


def _apply_common_filters(
    q: Query,
    model,
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    username: Optional[str],
    result: Optional[str],
    ip: Optional[str],
    device_name: Optional[str],
) -> Query:
    if date_from:
        q = q.filter(model.created_at >= date_from)
    if date_to:
        q = q.filter(model.created_at <= date_to)
    if username:
        q = q.filter(model.username.ilike(f"%{username}%"))
    if result:
        q = q.filter(model.result == result)
    if ip:
        q = q.filter(model.ip == ip)
    if device_name:
        q = q.filter(model.device_name.ilike(f"%{device_name}%"))
    return q


def _paginate(q: Query, model, page: int, page_size: int) -> tuple[list, int]:
    total = q.count()
    items = q.order_by(model.created_at.desc(), model.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def list_audit_logs(
    db: Session, *, page: int, page_size: int, event_type: Optional[str] = None, **filters: Any
) -> AuditLogListResponse:
    q = _apply_common_filters(db.query(AuditLog), AuditLog, **filters)
    if event_type:
        q = q.filter(AuditLog.event_type == event_type)
    items, total = _paginate(q, AuditLog, page, page_size)
    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)


def list_action_logs(
    db: Session,
    *,
    page: int,
    page_size: int,
    action: Optional[str] = None,
    method: Optional[str] = None,
    resource_type: Optional[str] = None,
    **filters: Any,
) -> ActionLogListResponse:
    q = _apply_common_filters(db.query(ActionLog), ActionLog, **filters)
    if action:
        q = q.filter(ActionLog.action.ilike(f"%{action}%"))
    if method:
        q = q.filter(ActionLog.method == method.upper())
    if resource_type:
        q = q.filter(ActionLog.resource_type == resource_type)
    items, total = _paginate(q, ActionLog, page, page_size)
    return ActionLogListResponse(items=items, total=total, page=page, page_size=page_size)


def cleanup_expired_logs(db: Session) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    audit_cutoff = now - timedelta(days=settings.audit_log_retention_days)
    action_cutoff = now - timedelta(days=settings.action_log_retention_days)
    deleted_audit = db.query(AuditLog).filter(AuditLog.created_at < audit_cutoff).delete(synchronize_session=False)
    deleted_action = db.query(ActionLog).filter(ActionLog.created_at < action_cutoff).delete(synchronize_session=False)
    db.commit()
    return {"audit_logs": deleted_audit, "action_logs": deleted_action}
