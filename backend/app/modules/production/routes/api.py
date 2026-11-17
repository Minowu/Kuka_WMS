"""REST API: Production Routes CRUD (thin router)."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production.routes import service as route_service
from app.modules.production.routes.schema import (
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
)

routes_router = APIRouter(tags=["Production - Routes"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@routes_router.get(
    "/production/routes",
    response_model=list[ProductionRouteResponse],
)
def list_production_routes(
    db: DbSession,
    _user: CurrentUser,
    item_id: Optional[int] = Query(None, description="Lọc theo Item ID"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
):
    return route_service.list_routes(db, item_id=item_id, is_active=is_active)


@routes_router.get(
    "/production/routes/{route_id}",
    response_model=ProductionRouteDetailResponse,
)
def get_production_route(
    route_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.get_route_detail(db, route_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@routes_router.post(
    "/production/routes",
    response_model=ProductionRouteDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_production_route(
    payload: ProductionRouteCreate,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.create_route(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@routes_router.put(
    "/production/routes/{route_id}",
    response_model=ProductionRouteDetailResponse,
)
def update_production_route(
    route_id: int,
    payload: ProductionRouteUpdate,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.update_route(db, route_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@routes_router.patch(
    "/production/routes/{route_id}/activate",
    response_model=ProductionRouteDetailResponse,
)
@routes_router.post(
    "/production/routes/{route_id}/activate",
    response_model=ProductionRouteDetailResponse,
)
def activate_production_route(
    route_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.activate_route(db, route_id)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "Không tìm thấy" in msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e


@routes_router.delete(
    "/production/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_production_route(
    route_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        route_service.delete_route(db, route_id)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "Không tìm thấy" in msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e
