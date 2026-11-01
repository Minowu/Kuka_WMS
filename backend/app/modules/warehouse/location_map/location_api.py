"""Location API."""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission, get_current_user
from app.modules.warehouse.location_map import location_service
from app.modules.warehouse.location_map.location_schema import (
    LocationDetailResponse,
    LocationListResponse,
    LocationQrPrintRequest,
    LocationQrPrintResponse,
    LocationResponse,
    LocationUpdate,
    LocationsByLogicResponse,
    LocationsForMapResponse,
    MapDataResponse,
    MapRemapEntry,
    MapSyncResult,
    ZoneMapLayoutResponse,
)

router = APIRouter(tags=["Location_Map"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/locations",
    response_model=LocationListResponse,
    dependencies=[Depends(require_permission("location:read"))],
)
def list_locations(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    warehouse_id: Optional[int] = Query(None),
    zone_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
):
    return location_service.list_locations(
        db,
        page=page,
        page_size=page_size,
        warehouse_id=warehouse_id,
        zone_id=zone_id,
        q=q,
    )


@router.get(
    "/locations/for-map",
    response_model=LocationsForMapResponse,
    dependencies=[Depends(require_permission("location:read"))],
)
def list_locations_for_map(
    db: DbSession,
    warehouse_id: int = Query(...),
):
    try:
        return location_service.list_locations_for_map(db, warehouse_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

@router.get(
    "/locations/zones/{zone_id}/for-map",
    response_model=LocationsForMapResponse,
    dependencies=[Depends(get_current_user)],
)
def list_locations_for_zone_map(
    db: DbSession,
    zone_id: int,
):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"API list_locations_for_zone_map called for zone {zone_id}")
    try:
        return location_service.list_locations_for_zone_map(db, zone_id)
    except ValueError as e:
        logger.error(f"ValueError in list_locations_for_zone_map for zone {zone_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Exception in list_locations_for_zone_map for zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/locations/by-logic",
    response_model=LocationsByLogicResponse,
    dependencies=[Depends(require_permission("location:read"))],
)
def list_locations_by_logic(
    db: DbSession,
    warehouse_id: int = Query(...),
    type: str = Query(..., description="Logic type, e.g. inbound_buffer"),
):
    try:
        locations = location_service.get_locations_by_logic(db, warehouse_id, type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return LocationsByLogicResponse(
        items=[LocationResponse.model_validate(loc) for loc in locations]
    )


@router.get(
    "/locations/{location_id}/detail",
    response_model=LocationDetailResponse,
    dependencies=[Depends(require_permission("location:read"))],
)
def get_location_detail(location_id: int, db: DbSession):
    try:
        return location_service.get_location_detail(db, location_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/locations/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(require_permission("location:read"))],
)
def get_location(location_id: int, db: DbSession):
    location = location_service.get_location_by_id(db, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationResponse.model_validate(location)


@router.patch(
    "/locations/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(require_permission("location:update"))],
)
def update_location(location_id: int, body: LocationUpdate, db: DbSession):
    try:
        location = location_service.update_location(db, location_id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return LocationResponse.model_validate(location)


@router.delete(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("location:delete"))],
)
def delete_location(location_id: int, db: DbSession):
    try:
        deleted = location_service.delete_location(db, location_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not deleted:
        raise HTTPException(status_code=404, detail="Location not found")
    return None


def _parse_remap_form(remap: Optional[str]) -> Optional[list[dict]]:
    """Remap arrives as a JSON string because the request is multipart/form-data."""
    if not remap or not remap.strip():
        return None
    try:
        parsed = json.loads(remap)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail="remap phải là JSON dạng [{from_bin, to_bin}]",
        ) from e
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=400,
            detail="remap phải là JSON dạng [{from_bin, to_bin}]",
        )
    try:
        entries = [MapRemapEntry.model_validate(item) for item in parsed]
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors()) from e
    return [entry.model_dump() for entry in entries]


def _require_zip(file: UploadFile) -> None:
    fn = (file.filename or "").lower()
    ct = (file.content_type or "").lower()
    if not (
        fn.endswith(".zip")
        or fn.endswith(".json")
        or "zip" in ct
        or "json" in ct
        or ct == "application/octet-stream"
    ):
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận file bản đồ định dạng .zip hoặc .json",
        )


@router.post(
    "/warehouse-maps/import/preview",
    response_model=MapSyncResult,
    dependencies=[Depends(require_permission("map:import_map"))],
)
async def preview_warehouse_map_import(
    db: DbSession,
    warehouse_id: int = Form(...),
    file: UploadFile = File(...),
    zone_id: Optional[int] = Form(None),
    remap: Optional[str] = Form(None),
):
    """Dry-run the import: report what would be matched, remapped and retired."""
    _require_zip(file)
    try:
        return await location_service.preview_warehouse_map_import(
            db=db,
            warehouse_id=warehouse_id,
            upload=file,
            zone_id=zone_id,
            remap=_parse_remap_form(remap),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/warehouse-maps/import",
    status_code=status.HTTP_201_CREATED,
    response_model=MapSyncResult,
    dependencies=[Depends(require_permission("map:import_map"))],
)
async def import_warehouse_map(
    db: DbSession,
    warehouse_id: int = Form(...),
    file: UploadFile = File(...),
    zone_id: Optional[int] = Form(None),
    remap: Optional[str] = Form(None),
):
    _require_zip(file)
    try:
        return await location_service.import_warehouse_map(
            db=db,
            warehouse_id=warehouse_id,
            upload=file,
            zone_id=zone_id,
            remap=_parse_remap_form(remap),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/warehouse-maps/{warehouse_id}/map-data",
    response_model=MapDataResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_permission("map:read"))],
)
def get_map_data(warehouse_id: int, db: DbSession):
    try:
        return location_service.get_map_data(db, warehouse_id)
    except ValueError as e:
        msg = str(e)
        status_code = (
            404 if "No active map" in msg or "not found" in msg.lower() else 400
        )
        raise HTTPException(status_code=status_code, detail=msg) from e

@router.get(
    "/warehouse-maps/zones/{zone_id}/map-data",
    response_model=ZoneMapLayoutResponse,
    dependencies=[Depends(get_current_user)],
)
def get_zone_map_data(zone_id: int, db: DbSession):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"API get_zone_map_data called for zone {zone_id}")
    try:
        return location_service.get_zone_map_layout(db, zone_id)
    except ValueError as e:
        logger.error(f"ValueError in get_zone_map_data for zone {zone_id}: {e}")
        msg = str(e)
        status_code = (
            404 if "No active map" in msg or "not found" in msg.lower() else 400
        )
        raise HTTPException(status_code=status_code, detail=msg) from e
    except Exception as e:
        logger.error(f"Exception in get_zone_map_data for zone {zone_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/warehouse-maps/{warehouse_id}/export",
    dependencies=[Depends(require_permission("map:export_map"))],
)
def export_warehouse_map(warehouse_id: int, db: DbSession):
    try:
        content, filename, media_type = location_service.export_warehouse_map(db, warehouse_id)
    except ValueError as e:
        msg = str(e)
        status_code = (
            404 if "No active map" in msg or "not found" in msg.lower() else 400
        )
        raise HTTPException(status_code=status_code, detail=msg) from e
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get(
    "/locations/by-logic/storage-area",
    response_model=LocationsByLogicResponse,
)
def list_locations_by_storage_area(db: DbSession, warehouse_id: int = Query(...), type: str = Query(...)):
    locations = location_service.get_locations_by_logic(db, warehouse_id, type)
    return LocationsByLogicResponse(
        items=[LocationResponse.model_validate(loc) for loc in locations]
    )


@router.post(
    "/locations/qr-codes/print",
    response_model=LocationQrPrintResponse,
    dependencies=[Depends(require_permission("location:read"))],
)
def print_location_qr_codes(body: LocationQrPrintRequest, db: DbSession):
    try:
        return location_service.generate_qr_location_code(
            db,
            body.location_ids,
            warehouse_id=body.warehouse_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e