"""Warehouse API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.warehouse.warehouse_zone import warehouse_service
from app.modules.warehouse.warehouse_zone.warehouse_schema import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseUpdate,
)

router = APIRouter(tags=["Warehouse"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/warehouses",
    response_model=WarehouseListResponse,
    dependencies=[Depends(get_current_user)],
)
def list_warehouses(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return warehouse_service.list_warehouses(db, page=page, page_size=page_size)


@router.post(
    "/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("warehouse:create"))],
)
def create_warehouse(body: WarehouseCreate, db: DbSession):
    try:
        warehouse = warehouse_service.create_warehouse(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WarehouseResponse.model_validate(warehouse)


@router.get(
    "/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
    dependencies=[Depends(get_current_user)],
)
def get_warehouse(warehouse_id: int, db: DbSession):
    warehouse = warehouse_service.get_warehouse_by_id(db, warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseResponse.model_validate(warehouse)


@router.patch(
    "/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
    dependencies=[Depends(require_permission("warehouse:update"))],
)
def update_warehouse(warehouse_id: int, body: WarehouseUpdate, db: DbSession):
    try:
        warehouse = warehouse_service.update_warehouse(db, warehouse_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return WarehouseResponse.model_validate(warehouse)


@router.delete(
    "/warehouses/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("warehouse:delete"))],
)
def delete_warehouse(warehouse_id: int, db: DbSession):
    try:
        deleted = warehouse_service.delete_warehouse(db, warehouse_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return None
