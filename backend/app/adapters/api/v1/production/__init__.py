"""Production API adapters — re-export thin routers (Strangler stable entry)."""

from app.modules.production.andon.api import andon_router
from app.modules.production.dispatch.api import dispatch_router
from app.modules.production.fleet.api import fleet_router
from app.modules.production.machine.api import machine_router
from app.modules.production.pda.api import pda_router
from app.modules.production.rack.api import rack_router
from app.modules.production.request.api import request_router
from app.modules.production.routes.aggregator import router as production_router
from app.modules.production.routes.api import routes_router
from app.modules.production.station.api import station_router
from app.modules.production.user_locations.api import user_locations_router

__all__ = [
    "andon_router",
    "dispatch_router",
    "fleet_router",
    "machine_router",
    "pda_router",
    "production_router",
    "rack_router",
    "request_router",
    "routes_router",
    "station_router",
    "user_locations_router",
]
