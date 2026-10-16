"""Production Route & Step Configuration API."""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.production import route_service
from app.modules.production.route_schema import (
    AvailableMachineResponse,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
)

router = APIRouter(prefix="/production", tags=["Production Route Configuration"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/machines",
    response_model=List[AvailableMachineResponse],
    dependencies=[Depends(get_current_user)],
    summary="Lấy danh sách mã máy CNC và vị trí docking có sẵn trong xưởng",
)
def list_available_machines(db: DbSession):
    return route_service.get_available_machines(db)


@router.get(
    "/routes",
    response_model=List[ProductionRouteResponse],
    dependencies=[Depends(get_current_user)],
    summary="Danh sách quy trình công nghệ gia công (có thể lọc theo Model hoặc Active)",
)
def list_routes(
    db: DbSession,
    item_id: Optional[int] = Query(None, description="Lọc theo Model sản phẩm"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
):
    return route_service.get_routes(db, item_id=item_id, is_active=is_active)


@router.get(
    "/routes/{route_id}",
    response_model=ProductionRouteDetailResponse,
    dependencies=[Depends(get_current_user)],
    summary="Xem chi tiết quy trình công nghệ và danh sách các bước gia công",
)
def get_route_detail(route_id: int, db: DbSession):
    route = route_service.get_route_by_id(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy trình công nghệ")
    return route


@router.post(
    "/routes",
    response_model=ProductionRouteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
    summary="Tạo mới quy trình công nghệ và thiết lập các bước gia công",
)
def create_route(payload: ProductionRouteCreate, db: DbSession):
    try:
        return route_service.create_route(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put(
    "/routes/{route_id}",
    response_model=ProductionRouteDetailResponse,
    dependencies=[Depends(get_current_user)],
    summary="Cập nhật thông tin quy trình và cấu hình lại danh sách các bước",
)
def update_route(route_id: int, payload: ProductionRouteUpdate, db: DbSession):
    try:
        route = route_service.update_route(db, route_id, payload)
        if not route:
            raise HTTPException(status_code=404, detail="Không tìm thấy quy trình cần cập nhật")
        return route
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch(
    "/routes/{route_id}/activate",
    response_model=ProductionRouteDetailResponse,
    dependencies=[Depends(get_current_user)],
    summary="Kích hoạt quy trình này làm quy trình chuẩn cho Model sản phẩm",
)
def activate_route(route_id: int, db: DbSession):
    route = route_service.set_active_route(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy trình cần kích hoạt")
    return route


@router.delete(
    "/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_user)],
    summary="Xóa quy trình công nghệ",
)
def delete_route(route_id: int, db: DbSession):
    success = route_service.delete_route(db, route_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy quy trình cần xóa")
    return None
