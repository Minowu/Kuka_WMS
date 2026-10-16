# Ensure dependent mappers are registered
import app.modules.auth.auth_model  # noqa: F401
import app.modules.warehouse.warehouse_zone.warehouse_model  # noqa: F401
import app.modules.warehouse.notificcation.notification_model  # noqa: F401

from app.modules.production.production_models import (
    UserLocation,
    ProductionRoute,
    RouteStep,
    TransportRequest,
    TransportQueue,
    FleetTask,
    ProductionRecord,
)
from app.modules.production.dispatch_service import DispatchService

__all__ = [
    "UserLocation",
    "ProductionRoute",
    "RouteStep",
    "TransportRequest",
    "TransportQueue",
    "FleetTask",
    "ProductionRecord",
]
