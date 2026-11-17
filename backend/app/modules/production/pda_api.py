"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.pda.api import pda_router

__all__ = ['pda_router']
