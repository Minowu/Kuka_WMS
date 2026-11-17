"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.station.api import station_router

__all__ = ['station_router']
