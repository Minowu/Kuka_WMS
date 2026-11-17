"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.rack.api import rack_router

__all__ = ['rack_router']
