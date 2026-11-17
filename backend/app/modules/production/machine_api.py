"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.machine.api import machine_router

__all__ = ['machine_router']
