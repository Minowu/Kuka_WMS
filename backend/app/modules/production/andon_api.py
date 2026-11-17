"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.andon.api import andon_router

__all__ = ['andon_router']
