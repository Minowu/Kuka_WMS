"""Inventory transaction ledger API (create + read only)."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.modules.auth.auth_model import User
from app.modules.warehouse.transaction_history import history_service
from app.modules.warehouse.transaction_history.history_schema import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    HistoryCreate,
    HistoryResponse,
    HistoryListResponse,
    TransactionHistoryLookupResponse,
)

router = APIRouter(tags=["Transaction_History"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    dependencies=[Depends(require_permission("transaction:read"))],
)
def list_transactions(
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_stock_id: Optional[int] = Query(None),
    from_location_id: Optional[int] = Query(None),
    to_location_id: Optional[int] = Query(None),
    transaction_type: Optional[str] = Query(None),
):
    return history_service.list_transactions(
        db,
        page=page,
        page_size=page_size,
        item_stock_id=item_stock_id,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        transaction_type=transaction_type,
    )


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("transaction:create"))],
)
def create_transaction(
    body: TransactionCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    try:
        tx = history_service.create_transaction(
            db, body, created_by_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return TransactionResponse.model_validate(tx)


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
    dependencies=[Depends(require_permission("transaction:read"))],
)
def get_transaction(transaction_id: int, db: DbSession):
    tx = history_service.get_transaction_by_id(db, transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(tx)


@router.post(
    "/histories",
    response_model=HistoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("history:create"))],
)
def create_history(body: HistoryCreate, db: DbSession, current_user: CurrentUser):
    try:
        history = history_service.create_history(db, body, created_by_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return HistoryResponse.model_validate(history)


@router.get(
    "/histories/{history_id}",
    response_model=HistoryResponse,
    dependencies=[Depends(require_permission("history:read"))],
)
def get_history(history_id: int, db: DbSession):
    history = history_service.get_history_by_id(db, history_id)
    if not history:
        raise HTTPException(status_code=404, detail="History not found")
    return HistoryResponse.model_validate(history)

@router.get(
    "/histories",
    response_model=HistoryListResponse,
    dependencies=[Depends(require_permission("history:read"))],
)
def list_histories(db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), inbound_order_id: Optional[int] = Query(None), outbound_order_id: Optional[int] = Query(None)):
    return history_service.list_histories(db, page=page, page_size=page_size, inbound_order_id=inbound_order_id, outbound_order_id=outbound_order_id)


@router.get(
    "/transaction-history",
    response_model=TransactionHistoryLookupResponse,
    dependencies=[Depends(require_permission("transaction:read"))],
)
def get_transaction_history(
    db: DbSession,
    qr_code: Optional[str] = Query(None, min_length=1),
    order_code: Optional[str] = Query(None, min_length=1),
):
    if qr_code and order_code is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide either qr_code or order_code, not both",
        )
    try:
        return history_service.get_transaction_history(
            db,
            qr_code=qr_code,
            order_code=order_code,
        )
    except ValueError as e:
        message = str(e)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from e

