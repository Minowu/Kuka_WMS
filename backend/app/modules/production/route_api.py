"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.routes.aggregator import router

__all__ = ['router']
