"""Compatibility re-export — implementation moved to feature package."""

from app.modules.production.routes.schema import *  # noqa: F403
from app.modules.production.dispatch.schema import *  # noqa: F403
from app.modules.production.pda.schema import *  # noqa: F403

__all__ = ['*']
