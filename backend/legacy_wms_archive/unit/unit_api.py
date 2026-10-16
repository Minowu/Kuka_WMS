"""Unit and ItemUnit API."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.warehouse.unit import unit_service
from app.modules.warehouse.unit.unit_service import item_unit_to_response
from app.modules.warehouse.unit.unit_schema import (
    ConvertQuantityRequest,
    ConvertQuantityResponse,
    ItemAvailableUnitsResponse,
    ItemUnitCreate,
    ItemUnitListResponse,
    ItemUnitResponse,
    ItemUnitUpdate,
    UnitCreate,
    UnitListResponse,
    UnitResponse,
    UnitUpdate,
)

router = APIRouter(tags=["Unit"])

DbSession = Annotated[Session, Depends(get_db)]


# --- Unit ---

@router.get(
    "/units",
    response_model=UnitListResponse,
)
def list_units(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None),
):
    return unit_service.list_units(db, page=page, page_size=page_size, q=q)


@router.post(
    "/units",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("unit:create"))],
)
def create_unit(body: UnitCreate, db: DbSession):
    try:
        unit = unit_service.create_unit(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return UnitResponse.model_validate(unit)


@router.get(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("unit:read"))],
)
def get_unit(unit_id: int, db: DbSession):
    unit = unit_service.get_unit_by_id(db, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return UnitResponse.model_validate(unit)


@router.patch(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("unit:update"))],
)
def update_unit(unit_id: int, body: UnitUpdate, db: DbSession):
    try:
        unit = unit_service.update_unit(db, unit_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return UnitResponse.model_validate(unit)


@router.delete(
    "/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("unit:delete"))],
)
def delete_unit(unit_id: int, db: DbSession):
    try:
        deleted = unit_service.delete_unit(db, unit_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Unit not found")
    return None


# --- ItemUnit ---

@router.get(
    "/item-units",
    response_model=ItemUnitListResponse,
    dependencies=[Depends(require_permission("item_unit:read"))],
)
def list_item_units(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: Optional[int] = Query(None),
    unit_id: Optional[int] = Query(None),
):
    return unit_service.list_item_units(
        db,
        page=page,
        page_size=page_size,
        item_id=item_id,
        unit_id=unit_id,
    )


@router.get(
    "/item-units/by-item/{item_id}",
    response_model=ItemAvailableUnitsResponse
)
def get_item_units_by_item(item_id: int, db: DbSession):
    try:
        return unit_service.get_item_unit_by_item(db, item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/item-units/convert-quantity",
    response_model=ConvertQuantityResponse,
)
def convert_item_quantity(body: ConvertQuantityRequest, db: DbSession):
    try:
        return unit_service.convert_quantity(
            db,
            item_id=body.item_id,
            unit_id=body.unit_id,
            quantity=body.quantity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/item-units",
    response_model=ItemUnitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("item_unit:create"))],
)
def create_item_unit(body: ItemUnitCreate, db: DbSession):
    try:
        item_unit = unit_service.create_item_unit(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return item_unit_to_response(item_unit)


@router.get(
    "/item-units/{item_unit_id}",
    response_model=ItemUnitResponse,
    dependencies=[Depends(require_permission("item_unit:read"))],
)
def get_item_unit(item_unit_id: int, db: DbSession):
    item_unit = unit_service.get_item_unit_by_id(db, item_unit_id)
    if not item_unit:
        raise HTTPException(status_code=404, detail="Item unit not found")
    return item_unit_to_response(item_unit)


@router.patch(
    "/item-units/{item_unit_id}",
    response_model=ItemUnitResponse,
    dependencies=[Depends(require_permission("item_unit:update"))],
)
def update_item_unit(item_unit_id: int, body: ItemUnitUpdate, db: DbSession):
    try:
        item_unit = unit_service.update_item_unit(db, item_unit_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not item_unit:
        raise HTTPException(status_code=404, detail="Item unit not found")
    return item_unit_to_response(item_unit)


@router.delete(
    "/item-units/{item_unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("item_unit:delete"))],
)
def delete_item_unit(item_unit_id: int, db: DbSession):
    try:
        deleted = unit_service.delete_item_unit(db, item_unit_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Item unit not found")
    return None
