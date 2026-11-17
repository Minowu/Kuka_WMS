"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.dispatch.service import DispatchService, dispatch_service

__all__ = ['DispatchService', 'dispatch_service']
