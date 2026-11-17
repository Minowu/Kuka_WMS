"""Production API aggregator — thin include_router only (no business logic)."""

from fastapi import APIRouter

from app.modules.production.andon.api import andon_router
from app.modules.production.dispatch.api import dispatch_router
from app.modules.production.fleet.api import fleet_router
from app.modules.production.machine.api import machine_router as machines_router
from app.modules.production.pda.api import pda_router
from app.modules.production.routes.api import routes_router
from app.modules.production.station.api import station_router as stations_router
from app.modules.production.user_locations.api import user_locations_router

router = APIRouter()

router.include_router(routes_router)
router.include_router(stations_router)
router.include_router(machines_router)
router.include_router(andon_router)
router.include_router(dispatch_router)
router.include_router(pda_router)
router.include_router(user_locations_router)
router.include_router(fleet_router)
