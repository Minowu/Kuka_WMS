"""Dispatch / AMR feature package."""

from app.modules.production.dispatch.kuka_fleet_client import IcsError
from app.modules.production.dispatch.service import DispatchService, dispatch_service

__all__ = ["DispatchService", "dispatch_service", "IcsError"]
