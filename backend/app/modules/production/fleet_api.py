"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.fleet.api import fleet_router

__all__ = ['fleet_router']
