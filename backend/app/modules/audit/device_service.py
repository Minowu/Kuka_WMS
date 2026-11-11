"""IP -> device registry: CRUD + small in-process cache used on every logged request."""
from __future__ import annotations

import threading
import time
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.audit.audit_model import Device
from app.modules.audit.audit_schema import DeviceCreate, DeviceUpdate

CACHE_TTL_SECONDS = 60

_cache: dict[str, tuple[str, str]] = {}
_cache_loaded_at = 0.0
_cache_lock = threading.Lock()


def invalidate_device_cache() -> None:
    global _cache_loaded_at
    with _cache_lock:
        _cache_loaded_at = 0.0


def resolve_device(db: Session, ip: Optional[str]) -> Optional[tuple[str, str]]:
    """Return ``(name, device_type)`` for a registered active IP, else None."""
    global _cache, _cache_loaded_at
    if not ip:
        return None
    with _cache_lock:
        if time.monotonic() - _cache_loaded_at > CACHE_TTL_SECONDS:
            rows = db.query(Device).filter(Device.is_active.is_(True)).all()
            _cache = {d.ip_address: (d.name, d.device_type) for d in rows}
            _cache_loaded_at = time.monotonic()
        return _cache.get(ip)


def list_devices(db: Session) -> list[Device]:
    return db.query(Device).order_by(Device.ip_address).all()


def create_device(db: Session, body: DeviceCreate) -> Device:
    device = Device(**body.model_dump())
    db.add(device)
    _commit_or_conflict(db, body.ip_address)
    db.refresh(device)
    invalidate_device_cache()
    return device


def update_device(db: Session, device_id: int, body: DeviceUpdate) -> Optional[Device]:
    device = db.get(Device, device_id)
    if not device:
        return None
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    _commit_or_conflict(db, device.ip_address)
    db.refresh(device)
    invalidate_device_cache()
    return device


def delete_device(db: Session, device_id: int) -> bool:
    device = db.get(Device, device_id)
    if not device:
        return False
    db.delete(device)
    db.commit()
    invalidate_device_cache()
    return True


def _commit_or_conflict(db: Session, ip_address: str) -> None:
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"IP {ip_address} đã được gán cho thiết bị khác") from e
