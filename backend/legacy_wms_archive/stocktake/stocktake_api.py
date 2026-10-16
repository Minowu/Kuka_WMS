"""Stocktake header CRUD API."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.auth.auth_model import User
from app.modules.warehouse.stocktake import stocktake_service
from app.modules.warehouse.stocktake.stocktake_service import stocktake_to_response
from app.modules.warehouse.stocktake.stocktake_schema import (
    StocktakeConfirmQuantityRequest,
    StocktakeCreate,
    StocktakeDetailResponse,
    StocktakeItemStockFormData,
    StocktakeItemStockListResponse,
    StocktakeItemStockResponse,
    StocktakeListResponse,
    StocktakeRecordCountRequest,
    StocktakeResponse,
    StocktakeUpdate,
)

router = APIRouter(tags=["Stocktake"])

DbSession = Annotated[Session, Depends(get_db)]

_STOCKTAKE_READ = require_permission("stocktake:read")
_STOCKTAKE_CREATE = require_permission("stocktake:create")
_STOCKTAKE_UPDATE = require_permission("stocktake:update")
_STOCKTAKE_DELETE = require_permission("stocktake:delete")


@router.get(
    "/stocktakes",
    response_model=StocktakeListResponse,
    dependencies=[Depends(_STOCKTAKE_READ)],
)
def list_stocktakes(
    db: DbSession,
    warehouse_id: int = Query(..., gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Tìm theo mô tả phiếu kiểm kê"),
):
    return stocktake_service.list_stocktakes(
        db,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
        q=q,
    )


@router.get(
    "/stocktake-items",
    response_model=StocktakeItemStockListResponse,
    dependencies=[Depends(_STOCKTAKE_READ)],
)
def list_stocktake_items(
    db: DbSession,
    warehouse_id: int = Query(..., gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stocktake_id: Optional[int] = Query(None, gt=0),
    statuses: Optional[str] = Query(
        None,
        description="Comma-separated item statuses, e.g. initialize,in_progress",
    ),
):
    status_list = (
        [part.strip() for part in statuses.split(",") if part.strip()]
        if statuses
        else None
    )
    return stocktake_service.list_stocktake_items(
        db,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
        stocktake_id=stocktake_id,
        statuses=status_list,
    )


@router.get(
    "/stocktake-items/{stocktake_item_id}/form-data",
    response_model=StocktakeItemStockFormData,
    dependencies=[Depends(_STOCKTAKE_READ)],
)
def get_stocktake_item_form_data(stocktake_item_id: int, db: DbSession):
    form_data = stocktake_service.get_stocktake_item_form_data(db, stocktake_item_id)
    if not form_data:
        raise HTTPException(status_code=404, detail="Stocktake item not found")
    return form_data


@router.post(
    "/stocktakes",
    response_model=StocktakeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stocktake(
    body: StocktakeCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(_STOCKTAKE_CREATE)],
):
    try:
        stocktake = stocktake_service.create_stocktake(
            db,
            body,
            location_ids=body.location_ids,
            item_ids=body.item_ids,
            lot_numbers=body.lot_numbers,
            created_by_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return stocktake_to_response(stocktake)


@router.get(
    "/stocktakes/{stocktake_id}",
    response_model=StocktakeDetailResponse,
    dependencies=[Depends(_STOCKTAKE_READ)],
)
def get_stocktake(stocktake_id: int, db: DbSession):
    detail = stocktake_service.get_stocktake_detail(db, stocktake_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Stocktake not found")
    return detail


@router.patch(
    "/stocktakes/{stocktake_id}",
    response_model=StocktakeResponse,
    dependencies=[Depends(_STOCKTAKE_UPDATE)],
)
def update_stocktake(stocktake_id: int, body: StocktakeUpdate, db: DbSession):
    try:
        stocktake = stocktake_service.update_stocktake(db, stocktake_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not stocktake:
        raise HTTPException(status_code=404, detail="Stocktake not found")
    return stocktake_to_response(stocktake)


@router.delete(
    "/stocktakes/{stocktake_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_STOCKTAKE_DELETE)],
)
def delete_stocktake(stocktake_id: int, db: DbSession):
    try:
        deleted = stocktake_service.delete_stocktake(db, stocktake_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Stocktake not found")
    return None


@router.post(
    "/stocktakes/{stocktake_id}/items/{stocktake_item_id}/record-count",
    response_model=StocktakeItemStockResponse,
    dependencies=[Depends(_STOCKTAKE_UPDATE)],
)
def record_stocktake_item_count(
    stocktake_id: int,
    stocktake_item_id: int,
    body: StocktakeRecordCountRequest,
    db: DbSession,
):
    try:
        result = stocktake_service.record_stocktake_item_count(
            db,
            stocktake_id,
            stocktake_item_id,
            body,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not result:
        raise HTTPException(status_code=404, detail="Stocktake item not found")
    return result


@router.post(
    "/stocktakes/{stocktake_id}/items/{stocktake_item_id}/confirm-quantity",
    response_model=StocktakeItemStockResponse,
    dependencies=[Depends(_STOCKTAKE_UPDATE)],
)
def confirm_stocktake_item_quantity(
    stocktake_id: int,
    stocktake_item_id: int,
    db: DbSession,
    body: StocktakeConfirmQuantityRequest | None = None,
):
    try:
        result = stocktake_service.confirm_quantity_for_stock(
            db,
            stocktake_id,
            stocktake_item_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not result:
        raise HTTPException(status_code=404, detail="Stocktake item not found")
    return result
