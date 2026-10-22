from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production import station_service
from app.modules.production.station_schema import (
    StationCatalogResponse,
    StationCatalogItem,
    StationSlotCreateRequest,
    StationSlotUpdateRequest,
    MapAvailableNodeResponse,
)

station_router = APIRouter(tags=["Production - Stations & Layout"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# =========================================================================
# 1. MAP AVAILABLE NODES (GROUND TRUTH) & SHOP STATIONS CATALOG
# =========================================================================

@station_router.get(
    "/production/map/available-nodes",
    response_model=list[MapAvailableNodeResponse],
)
def get_available_map_nodes(
    db: DbSession,
    _user: CurrentUser,
    only_rack: bool = Query(True, description="Chỉ lấy các Node kệ/điểm đỗ vận hành (functionType == 2)"),
    only_functional: bool = Query(True, description="Chỉ lấy các Node có functionType"),
):
    """Lấy danh sách các Node điểm đỗ/kệ từ bản đồ chuẩn xưởng kèm trạng thái gán."""
    try:
        return station_service.get_available_map_nodes(
            db, only_functional=only_functional, rack_only=only_rack
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@station_router.get(
    "/production/stations/catalog",
    response_model=StationCatalogResponse,
)
def get_station_catalog(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh mục hợp nhất toàn bộ trạm xưởng (Nguyên liệu, Tẩy rửa, Bãi đệm, Máy CNC 1..3 slots)."""
    return station_service.get_station_catalog(db)


# =========================================================================
# 2. GENERIC SHOP LOCATIONS (RAW MATERIAL, WASHING, BUFFER)
# =========================================================================

@station_router.post(
    "/production/stations/locations",
    response_model=StationCatalogItem,
    status_code=status.HTTP_201_CREATED,
)
def create_station_location(
    payload: StationSlotCreateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    loc_type = payload.location_type or "RAW_MATERIAL"
    try:
        return station_service.create_station_slot(db, loc_type, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@station_router.put(
    "/production/stations/locations/{location_id}",
    response_model=StationCatalogItem,
)
def update_station_location(
    location_id: int,
    payload: StationSlotUpdateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return station_service.update_station_slot(db, location_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@station_router.delete(
    "/production/stations/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_station_location(
    location_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        station_service.delete_station_slot(db, location_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

