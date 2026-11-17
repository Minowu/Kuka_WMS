"""Service layer for managing Production Routes and Route Steps (3NF)."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.modules.production.production_models import (
    Machine,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportRequest,
)
from app.modules.production.routes.schema import (
    ItemSummary,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RouteStepResponse,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

log = get_logger("wms.domain.production")

ACTIVE_ROUTE_REQUEST_STATUSES = (
    "pending",
    "queued_for_cart",
    "queued_for_slot",
    "in_progress",
)



from app.modules.production.routes.service_pkg.helpers import (
    _to_route_response,
)

def list_routes(
    db: Session,
    item_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> list[ProductionRouteResponse]:
    query = db.query(ProductionRoute).options(
        joinedload(ProductionRoute.item),
        joinedload(ProductionRoute.steps)
        .selectinload(RouteStep.allowed_machine_links)
        .joinedload(RouteStepMachine.machine),
    )
    if item_id is not None:
        query = query.filter(ProductionRoute.item_id == item_id)
    if is_active is not None:
        query = query.filter(ProductionRoute.is_active == is_active)

    routes = query.order_by(ProductionRoute.item_id.asc(), ProductionRoute.version.desc()).all()
    return [_to_route_response(r, include_steps=False) for r in routes]


def get_route_detail(db: Session, route_id: int) -> ProductionRouteDetailResponse:
    route = (
        db.query(ProductionRoute)
        .options(
            joinedload(ProductionRoute.item),
            joinedload(ProductionRoute.steps)
            .selectinload(RouteStep.allowed_machine_links)
            .joinedload(RouteStepMachine.machine),
        )
        .filter(ProductionRoute.id == route_id)
        .first()
    )
    if not route:
        raise ValueError(f"Không tìm thấy quy trình sản xuất ID={route_id}")
    return _to_route_response(route, include_steps=True)


