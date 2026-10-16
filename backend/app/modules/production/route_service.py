"""Service layer for Production Route and Route Step operations."""

from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.production.production_models import ProductionRoute, RouteStep
from app.modules.production.route_schema import (
    AvailableMachineResponse,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RouteStepResponse,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.location_map.location_model import Location


def get_routes(
    db: Session,
    item_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> List[ProductionRouteResponse]:
    """Retrieve list of production routes with optional filters."""
    query = db.query(ProductionRoute)

    if item_id is not None:
        query = query.filter(ProductionRoute.item_id == item_id)
    if is_active is not None:
        query = query.filter(ProductionRoute.is_active.is_(is_active))

    routes = query.order_by(ProductionRoute.created_at.desc()).all()

    result = []
    for r in routes:
        resp = ProductionRouteResponse.model_validate(r)
        resp.step_count = len(r.steps) if r.steps else 0
        result.append(resp)
    return result


def get_route_by_id(db: Session, route_id: int) -> Optional[ProductionRouteDetailResponse]:
    """Retrieve detailed route including all technological steps ordered by step_number."""
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        return None

    resp = ProductionRouteDetailResponse.model_validate(route)
    resp.step_count = len(route.steps) if route.steps else 0
    resp.steps = [RouteStepResponse.model_validate(s) for s in sorted(route.steps, key=lambda x: x.step_number)]
    return resp


def create_route(db: Session, payload: ProductionRouteCreate) -> ProductionRouteDetailResponse:
    """Create a new production route and its process steps in a single transaction."""
    # 1. Check if route_code exists
    existing = db.query(ProductionRoute).filter(ProductionRoute.route_code == payload.route_code).first()
    if existing:
        raise ValueError(f"Mã quy trình '{payload.route_code}' đã tồn tại trong hệ thống")

    # 2. Check if item exists
    item = db.query(Item).filter(Item.id == payload.item_id).first()
    if not item:
        raise ValueError(f"Không tìm thấy Model sản phẩm có ID={payload.item_id}")

    # 3. If new route is active, deactivate other routes for this item
    if payload.is_active:
        db.query(ProductionRoute).filter(
            ProductionRoute.item_id == payload.item_id,
            ProductionRoute.is_active.is_(True),
        ).update({"is_active": False})

    # 4. Create route
    route = ProductionRoute(
        route_code=payload.route_code.strip(),
        route_name=payload.route_name.strip(),
        item_id=payload.item_id,
        version=payload.version,
        is_active=payload.is_active,
    )
    db.add(route)
    db.flush()

    # 5. Create steps
    for step_data in payload.steps:
        step = RouteStep(
            route_id=route.id,
            step_number=step_data.step_number,
            stage_level=step_data.stage_level,
            step_name=step_data.step_name.strip(),
            allowed_machines=step_data.allowed_machines,
            is_final_cnc_step=step_data.is_final_cnc_step,
        )
        db.add(step)

    db.commit()
    db.refresh(route)
    return get_route_by_id(db, route.id)  # type: ignore


def update_route(
    db: Session,
    route_id: int,
    payload: ProductionRouteUpdate,
) -> Optional[ProductionRouteDetailResponse]:
    """Update route information and optionally replace its steps."""
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        return None

    if payload.route_name is not None:
        route.route_name = payload.route_name.strip()
    if payload.version is not None:
        route.version = payload.version
    if payload.is_active is not None:
        if payload.is_active:
            # Deactivate other routes for the same item
            db.query(ProductionRoute).filter(
                ProductionRoute.item_id == route.item_id,
                ProductionRoute.id != route.id,
                ProductionRoute.is_active.is_(True),
            ).update({"is_active": False})
        route.is_active = payload.is_active

    # If steps are supplied, replace all existing steps
    if payload.steps is not None:
        db.query(RouteStep).filter(RouteStep.route_id == route.id).delete()
        db.flush()
        for step_data in payload.steps:
            new_step = RouteStep(
                route_id=route.id,
                step_number=step_data.step_number,
                stage_level=step_data.stage_level,
                step_name=step_data.step_name.strip(),
                allowed_machines=step_data.allowed_machines,
                is_final_cnc_step=step_data.is_final_cnc_step,
            )
            db.add(new_step)

    db.commit()
    db.refresh(route)
    return get_route_by_id(db, route.id)


def set_active_route(db: Session, route_id: int) -> Optional[ProductionRouteDetailResponse]:
    """Activate this route and deactivate all other routes for the same item."""
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        return None

    # Deactivate others
    db.query(ProductionRoute).filter(
        ProductionRoute.item_id == route.item_id,
        ProductionRoute.id != route.id,
        ProductionRoute.is_active.is_(True),
    ).update({"is_active": False})

    route.is_active = True
    db.commit()
    db.refresh(route)
    return get_route_by_id(db, route.id)


def delete_route(db: Session, route_id: int) -> bool:
    """Delete a route and cascade-delete its steps."""
    route = db.query(ProductionRoute).filter(ProductionRoute.id == route_id).first()
    if not route:
        return False

    db.delete(route)
    db.commit()
    return True


def get_available_machines(db: Session) -> List[AvailableMachineResponse]:
    """Fetch distinct machine codes and their physical docking positions."""
    locs = (
        db.query(Location)
        .filter(Location.machine_code.isnot(None), Location.is_active.is_(True))
        .all()
    )

    machine_map: Dict[str, List[str]] = {}
    for loc in locs:
        m_code = loc.machine_code.strip()
        if m_code not in machine_map:
            machine_map[m_code] = []
        if loc.code:
            machine_map[m_code].append(loc.code)

    # If database has no locations configured yet, return standard 4 CNC machines as fallback
    if not machine_map:
        return [
            AvailableMachineResponse(
                machine_code=f"CNC-0{i}",
                location_count=2,
                positions=[f"CNC0{i}_POS1", f"CNC0{i}_POS2"],
            )
            for i in range(1, 5)
        ]

    results = []
    for m_code in sorted(machine_map.keys()):
        positions = machine_map[m_code]
        results.append(
            AvailableMachineResponse(
                machine_code=m_code,
                location_count=len(positions),
                positions=positions,
            )
        )
    return results
