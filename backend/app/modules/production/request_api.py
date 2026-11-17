"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.request.api import request_router

__all__ = ['request_router']
