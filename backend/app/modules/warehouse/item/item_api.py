"""Item API (Product / CNC Model master data)."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.warehouse.item import item_service
from app.modules.warehouse.item.item_schema import (
    ItemAnalyzeResponse,
    ItemCreate,
    ItemDetailResponse,
    ItemImportJobAccepted,
    ItemImportJobStatus,
    ItemListResponse,
    ItemResponse,
    ItemUpdate,
)

router = APIRouter(tags=["Item"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/items",
    response_model=ItemListResponse,
)
def list_items(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
):
    return item_service.list_items(
        db,
        page=page,
        page_size=page_size,
        warehouse_id=warehouse_id,
        q=q,
        is_active=is_active,
    )


@router.get(
    "/items/analyze-items/{warehouse_id}",
    response_model=ItemAnalyzeResponse,
    dependencies=[Depends(get_current_user)],
)
def analyze_items(warehouse_id: int, db: DbSession):
    try:
        return item_service.analyze_items(db, warehouse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/items/import",
    response_model=ItemImportJobAccepted,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("item:create"))],
)
async def import_items_masan(
    db: DbSession,
    warehouse_id: int = Form(...),
    file: UploadFile = File(...),
):
    try:
        return await item_service.start_item_masan_import(db, warehouse_id, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/items/import/file",
    dependencies=[Depends(get_current_user)],
)
def download_last_import_item_file(
    db: DbSession,
    warehouse_id: int = Query(..., gt=0),
):
    try:
        file_path, filename = item_service.get_last_import_item_file(db, warehouse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename,
    )


@router.get(
    "/items/import/{job_id}",
    response_model=ItemImportJobStatus,
    dependencies=[Depends(require_permission("item:create"))],
)
def get_import_items_job(job_id: str):
    try:
        return item_service.get_item_import_job_status(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_item(body: ItemCreate, db: DbSession):
    try:
        item = item_service.create_item(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return ItemResponse.model_validate(item)


@router.get(
    "/items/{item_id}",
    response_model=ItemDetailResponse,
    dependencies=[Depends(get_current_user)],
)
def get_item(item_id: int, db: DbSession):
    try:
        return item_service.get_item_detail(db, item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch(
    "/items/{item_id}",
    response_model=ItemResponse,
    dependencies=[Depends(require_permission("item:update"))],
)
def update_item(item_id: int, body: ItemUpdate, db: DbSession):
    try:
        item = item_service.update_item(db, item_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse.model_validate(item)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("item:delete"))],
)
def delete_item(item_id: int, db: DbSession):
    try:
        deleted = item_service.delete_item(db, item_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return None
