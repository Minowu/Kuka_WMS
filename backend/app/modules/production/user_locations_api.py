"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.user_locations.api import user_locations_router

__all__ = ['user_locations_router']
