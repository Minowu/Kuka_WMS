"""Fleet webhook API adapter."""

from app.modules.production.fleet.api import fleet_router as webhook_router

__all__ = ["webhook_router"]
