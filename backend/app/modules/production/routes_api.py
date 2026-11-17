"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.routes.api import routes_router

__all__ = ['routes_router']
