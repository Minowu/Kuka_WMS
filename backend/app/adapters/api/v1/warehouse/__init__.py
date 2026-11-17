"""Warehouse API adapters — re-export from modules."""

from app.modules.warehouse.dashboard.dashboard_api import router as dashboard_router
from app.modules.warehouse.item.item_api import router as item_router
from app.modules.warehouse.item_stock.item_stock_api import router as item_stock_router
from app.modules.warehouse.location_map.location_api import router as location_router
from app.modules.warehouse.notificcation.notification_api import router as notification_router
from app.modules.warehouse.warehouse_zone.warehouse_api import router as warehouse_router

__all__ = [
    "dashboard_router",
    "item_router",
    "item_stock_router",
    "location_router",
    "notification_router",
    "warehouse_router",
]
