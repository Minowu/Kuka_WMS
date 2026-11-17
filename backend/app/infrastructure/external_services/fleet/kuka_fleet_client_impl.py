"""KUKA Fleet client — Strangler re-export from modules package."""

from app.modules.production.dispatch.kuka_fleet_client import (  # noqa: F401
    IcsError,
    KukaFleetClient,
)

__all__ = ["IcsError", "KukaFleetClient"]
