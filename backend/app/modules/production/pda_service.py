"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.pda.service import *  # noqa: F403

__all__ = [name for name in dir() if not name.startswith("_")]
