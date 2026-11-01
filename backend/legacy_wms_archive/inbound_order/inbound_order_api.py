from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.celery_app import run_logic_task
from app.core.database import get_db
from app.core.dependencies import get_dev_admin_user, require_permission
from app.modules.robot.robot_service import IcsError
from app.modules.auth.auth_model import User
from app.modules.warehouse.inbound_order import inbound_order_model
from app.modules.warehouse.inbound_order.inbound_order_schema import (
    InboundSuggestAllocation,
    InboundSuggestAllocationResponse,
    InboundReleaseLocationsRequest,
    InboundReleaseLocationsResponse,
    PurgePackingCacheResponse,
    InboundOrderCreate,
    InboundOrderResponse,
    InboundCallerResponse,
    InboundOrderListResponse,
    InboundOrderDetailResponse,
    InboundOrderUpdate,
    InboundOrderDeleteResponse,
    AssignOrGetItemStockRequest,
    AssignOrGetItemStockResponse,
    QrCodePreviewRequest,
    CacheForPackingUserRequest,
    AssignPackingToItemRequest,
    PackingUserPendingStocksResponse,
    RelocateAssignedStockRequest,
    RelocateAssignedStockResponse,
)
from app.modules.warehouse.inbound_order import inbound_order_service, qr_code_module
from app.modules.warehouse.inbound_order.inbound_celery_task import (
    accept_inbound_task_task,
    caller_inbound_order_task,
    create_inbound_order_task,
    get_inbound_order_details_task,
    update_inbound_order_task,
)

_INBOUND_READ = require_permission("inbound:read")
_INBOUND_CREATE = require_permission("inbound:create")
_INBOUND_UPDATE = require_permission("inbound:update")
_INBOUND_DELETE = require_permission("inbound:delete")

router = APIRouter(tags=["Inbound Order"])

DbSession = Annotated[Session, Depends(get_db)]

__all__ = [
    "router",
    "DbSession",
    "_INBOUND_READ",
    "_INBOUND_CREATE",
    "_INBOUND_UPDATE",
    "_INBOUND_DELETE",
]

@router.post(
    "/inbound-orders/suggest-allocation",
    response_model=InboundSuggestAllocationResponse,
)
def suggest_inbound_allocation(body: InboundSuggestAllocation, db: DbSession):
    try:
        return inbound_order_service.suggest_allocation_inbound(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/inbound-orders/release-locations",
    response_model=InboundReleaseLocationsResponse,
    dependencies=[Depends(_INBOUND_CREATE)],
)
def release_inbound_locations(body: InboundReleaseLocationsRequest):
    deleted = inbound_order_service.delete_allocated_locations(body.location_ids)
    return InboundReleaseLocationsResponse(deleted=deleted)


@router.post(
    "/inbound-orders/purge-packing-cache",
    response_model=PurgePackingCacheResponse,
    dependencies=[Depends(_INBOUND_CREATE)],
)
def purge_packing_cache():
    deleted = qr_code_module.delete_packing_cache()
    return PurgePackingCacheResponse(deleted=deleted)


@router.post(
    "/inbound-orders",
    response_model=InboundOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inbound_order(
    body: InboundOrderCreate,
    db: DbSession,
    current_user: Annotated[User, Depends(get_dev_admin_user)],
    inbound_type: str,
):
    try:
        order = run_logic_task(
            create_inbound_order_task,
            body=body.model_dump(mode="json"),
            user_id=current_user.id,
            inbound_type=inbound_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return InboundOrderResponse.model_validate(order)


@router.get(
    "/inbound-orders",
    response_model=InboundOrderListResponse,
)
def list_inbound_orders(
    db: DbSession,
    warehouse_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None, description="Tìm theo mã đơn hoặc người tạo"),
    status: Optional[str] = Query(None, description="Lọc trạng thái đơn"),
):
    orders, total, summary = inbound_order_service.get_inbound_order(
        db,
        warehouse_id=warehouse_id,
        page=page,
        page_size=page_size,
        q=q,
        status=status,
    )
    return InboundOrderListResponse(
        items=[InboundOrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        summary=summary,
    )


@router.get(
    "/inbound-orders/{order_code}/details",
    response_model=list[InboundOrderDetailResponse],
    dependencies=[Depends(_INBOUND_READ)],
)
def get_inbound_order_details(db: DbSession, order_code: str):
    try:
        details = run_logic_task(get_inbound_order_details_task, order_code=order_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if details is None:
        raise HTTPException(status_code=404, detail="Inbound order not found")
    return details

@router.post(
    "/inbound-allocations/{detail_id}/accept-task",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_INBOUND_UPDATE)],
)
def accept_inbound_task(db: DbSession, detail_id: int):
    try:
        task = run_logic_task(accept_inbound_task_task, detail_id=detail_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e 
    except IcsError as e:
        raise HTTPException(status_code=503 if "reach" in str(e).lower() else 502, detail=str(e)) from e
    return task

@router.patch(
    "/inbound-orders/{order_code}",
    response_model=InboundOrderResponse,
    dependencies=[Depends(_INBOUND_UPDATE)],
)
def update_inbound_order(order_code: str, body: InboundOrderUpdate, db: DbSession, inbound_type: str, current_user: Annotated[User, Depends(_INBOUND_UPDATE)],):
    try:
        order = run_logic_task(
            update_inbound_order_task,
            order_code=order_code,
            body=body.model_dump(mode="json"),
            inbound_type=inbound_type,
            user_id=current_user.id,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return InboundOrderResponse.model_validate(order)

@router.delete(
    "/inbound-orders/{order_code}",
    response_model=InboundOrderDeleteResponse,
    dependencies=[Depends(_INBOUND_DELETE)],
)
def delete_inbound_order(
    order_code: str,
    db: DbSession,
):
    try:
        inbound_order_service.delete_inbound_order(db, order_code)
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return InboundOrderDeleteResponse(
        order_code=order_code,
        message="Inbound order deleted",
    )

@router.post(
    "/inbound-orders/caller",
    status_code=status.HTTP_201_CREATED,
    response_model=InboundCallerResponse,
    # dependencies=[Depends(_INBOUND_CREATE)],
)
def caller_inbound_order(
    body: InboundOrderCreate,
    db: DbSession,
    inbound_type: str,
    # current_user: Annotated[User, Depends(_INBOUND_CREATE)],
):
    try:
        order = run_logic_task(
            caller_inbound_order_task,
            body=body.model_dump(mode="json"),
            user_id=1,
            inbound_type=inbound_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return InboundCallerResponse.model_validate(order)

@router.post(
    "/inbound-orders/preview-stocks",
    response_model=AssignOrGetItemStockResponse,
)
def preview_inbound_qr_code(
    body: QrCodePreviewRequest,
    db: DbSession,
):
    try:
        result = qr_code_module.preview_qr_code(
            db=db,
            qr_code=body.qr_code,
            warehouse_id=body.warehouse_id,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return AssignOrGetItemStockResponse.model_validate(result)


@router.post(
    "/inbound-orders/assigned-stocks",
    response_model=AssignOrGetItemStockResponse,
)
def assign_or_get_item_stocks(
    body: AssignOrGetItemStockRequest,
    db: DbSession,
):
    return _assign_or_get_item_stocks(db, body)


@router.post(
    "/inbound-orders/locations/{location_id}/assigned-stocks",
    response_model=AssignOrGetItemStockResponse,
)
def assign_or_get_item_stocks_by_location(
    location_id: int,
    body: AssignOrGetItemStockRequest,
    db: DbSession,
):
    payload = body.model_copy(update={"location_id": location_id})
    return _assign_or_get_item_stocks(db, payload)


def _assign_or_get_item_stocks(db: Session, body: AssignOrGetItemStockRequest):
    try:
        result = qr_code_module.assign_or_get_item_stock(
            db=db,
            raw=body.raw,
            warehouse_id=body.warehouse_id,
            qr_code=body.qr_code,
            quantity=body.quantity,
            unit_id=body.unit_id,
            lot_number=body.lot_number,
            cavity_number=body.cavity_number,
            manufacturing_user=body.manufacturing_user,
            manufacturing_machine=body.manufacturing_machine,
            qc_user=body.qc_user,
            packing_user=body.packing_user,
            is_split=body.is_split,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return AssignOrGetItemStockResponse.model_validate(result)


@router.post(
    "/inbound-orders/manual/scan",
    response_model=AssignOrGetItemStockResponse,
)
def manual_inbound_scan(
    body: AssignOrGetItemStockRequest,
    db: DbSession,
    current_user: Annotated[User, Depends(get_dev_admin_user)],
):
    try:
        result = qr_code_module.assign_stock_to_location(
            db=db,
            user_id=current_user.id,
            raw=body.raw,
            warehouse_id=body.warehouse_id,
            qr_code=body.qr_code,
            quantity=body.quantity,
            unit_id=body.unit_id,
            lot_number=body.lot_number,
            cavity_number=body.cavity_number,
            manufacturing_user=body.manufacturing_user,
            manufacturing_machine=body.manufacturing_machine,
            qc_user=body.qc_user,
            packing_user=body.packing_user,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return AssignOrGetItemStockResponse.model_validate(result)


@router.get(
    "/inbound-orders/packing-stocks",
    response_model=PackingUserPendingStocksResponse,
)
def get_packing_user_pending_stocks(
    packing_user: str = Query(..., min_length=1, max_length=100),
    linked: Optional[bool] = Query(
        None,
        description="True=linked packs only, False=unlinked packs only, omit=all pack pending",
    ),
    pending_role: Optional[Literal["item", "pack"]] = Query(
        None,
        description='"item"=item anchors (relation=item), "pack" or omit with linked=pack filters',
    ),
):
    try:
        items = qr_code_module.get_pending_by_packing_user(
            packing_user,
            linked=linked,
            pending_role=pending_role,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return PackingUserPendingStocksResponse(packing_user=packing_user.strip(), items=items)


@router.post(
    "/inbound-orders/item-assign/packing",
    response_model=AssignOrGetItemStockResponse,
)
def assign_packing_to_item(
    body: AssignPackingToItemRequest,
    db: DbSession,
):
    try:
        result = qr_code_module.assign_packing_to_item(
            db=db,
            target_qr_id=body.target_qr_id,
            warehouse_id=body.warehouse_id,
            qr_code=body.qr_code,
            quantity=body.quantity,
            unit_id=body.unit_id,
            lot_number=body.lot_number,
            cavity_number=body.cavity_number,
            manufacturing_user=body.manufacturing_user,
            manufacturing_machine=body.manufacturing_machine,
            qc_user=body.qc_user,
            packing_user=body.packing_user,
            is_split=body.is_split,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return AssignOrGetItemStockResponse.model_validate(result)


@router.post(
    "/inbound-orders/packing-stocks",
    response_model=AssignOrGetItemStockResponse,
)
def cache_for_packing_user(
    body: CacheForPackingUserRequest,
    db: DbSession,
):
    try:
        result = qr_code_module.assign_for_packing_user(
            db=db,
            warehouse_id=body.warehouse_id,
            qr_code=body.qr_code,
            quantity=body.quantity,
            unit_id=body.unit_id,
            lot_number=body.lot_number,
            cavity_number=body.cavity_number,
            manufacturing_user=body.manufacturing_user,
            manufacturing_machine=body.manufacturing_machine,
            qc_user=body.qc_user,
            packing_user=body.packing_user,
            relation=body.relation,
            is_split=body.is_split,
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
    return AssignOrGetItemStockResponse.model_validate(result)


@router.post(
    "/inbound-orders/assigned-stocks/relocate",
    response_model=RelocateAssignedStockResponse,
)
def relocate_assigned_stocks(
    body: RelocateAssignedStockRequest,
    db: DbSession,
):
    try:
        moved = qr_code_module.relocate_cached_item_stock(
            db=db,
            from_location_code=body.from_location_code.strip(),
            to_location_code=body.to_location_code.strip(),
        )
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e

    return RelocateAssignedStockResponse(
        moved=moved,
        from_location_code=body.from_location_code.strip(),
        to_location_code=body.to_location_code.strip(),
    )