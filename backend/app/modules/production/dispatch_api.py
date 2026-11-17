"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.dispatch.api import dispatch_router

__all__ = ['dispatch_router']
