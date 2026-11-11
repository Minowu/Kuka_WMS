"""Audit log, action log and device registry API."""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.audit import audit_service, device_service
from app.modules.audit.audit_schema import (
    ActionLogListResponse,
    AuditEventType,
    AuditLogListResponse,
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    LogResult,
)

router = APIRouter(tags=["Audit"])

DbSession = Annotated[Session, Depends(get_db)]

_AUDIT_READ = require_permission("audit:read")
_DEVICE_MANAGE = require_permission("device:manage")


class CommonLogFilters:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        date_from: Optional[datetime] = Query(None, description="ISO-8601, inclusive"),
        date_to: Optional[datetime] = Query(None, description="ISO-8601, inclusive"),
        username: Optional[str] = Query(None, description="Contains, case-insensitive"),
        result: Optional[LogResult] = Query(None),
        ip: Optional[str] = Query(None, description="Exact match"),
        device_name: Optional[str] = Query(None, description="Contains, case-insensitive"),
    ):
        self.page = page
        self.page_size = page_size
        self.filters = {
            "date_from": date_from,
            "date_to": date_to,
            "username": username,
            "result": result,
            "ip": ip,
            "device_name": device_name,
        }


Filters = Annotated[CommonLogFilters, Depends()]


@router.get("/audit-logs", response_model=AuditLogListResponse, dependencies=[Depends(_AUDIT_READ)])
def list_audit_logs(
    db: DbSession,
    common: Filters,
    event_type: Optional[AuditEventType] = Query(None),
):
    return audit_service.list_audit_logs(
        db, page=common.page, page_size=common.page_size, event_type=event_type, **common.filters
    )


@router.get("/action-logs", response_model=ActionLogListResponse, dependencies=[Depends(_AUDIT_READ)])
def list_action_logs(
    db: DbSession,
    common: Filters,
    action: Optional[str] = Query(None, description="Contains, case-insensitive"),
    method: Optional[str] = Query(None, description="POST | PUT | PATCH | DELETE"),
    resource_type: Optional[str] = Query(None),
):
    return audit_service.list_action_logs(
        db,
        page=common.page,
        page_size=common.page_size,
        action=action,
        method=method,
        resource_type=resource_type,
        **common.filters,
    )


@router.get("/devices", response_model=list[DeviceResponse], dependencies=[Depends(_AUDIT_READ)])
def list_devices(db: DbSession):
    return device_service.list_devices(db)


@router.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_DEVICE_MANAGE)],
)
def create_device(body: DeviceCreate, db: DbSession):
    try:
        return device_service.create_device(db, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.patch("/devices/{device_id}", response_model=DeviceResponse, dependencies=[Depends(_DEVICE_MANAGE)])
def update_device(device_id: int, body: DeviceUpdate, db: DbSession):
    try:
        device = device_service.update_device(db, device_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(_DEVICE_MANAGE)])
def delete_device(device_id: int, db: DbSession):
    if not device_service.delete_device(db, device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    return None
