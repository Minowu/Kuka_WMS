"""Inventory transaction ledger service.

Create only writes a ledger row. It does NOT update ItemStock quantities;
stock movement business logic belongs in a dedicated workflow later.
"""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.transaction_history.history_model import Transaction, History
from app.modules.warehouse.transaction_history.history_schema import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    HistoryCreate,
    HistoryResponse,
    HistoryListResponse,
    TransactionHistoryLookupResponse,
    ItemStockLookupResponse,
    TransactionHistoryItemResponse,
    OrderBriefResponse,
)
from app.modules.warehouse.item.item_model import QR_Code
from app.modules.warehouse.inbound_order.inbound_order_model import InboundOrder
from app.modules.warehouse.outbound_order.outbound_order_model import OutboundOrder


def _to_item_stock_lookup(stock: ItemStock) -> ItemStockLookupResponse:
    location = stock.location
    item = stock.item
    unit = stock.unit
    return ItemStockLookupResponse.model_validate(stock).model_copy(
        update={
            "item_sku": item.sku if item else None,
            "item_name": item.name if item else None,
            "location_code": location.location_code if location else None,
            "location_name": location.location_name if location else None,
            "unit_name": unit.name if unit else None,
        }
    )


def _to_transaction_history_item(tx: Transaction) -> TransactionHistoryItemResponse:
    from_location = tx.from_location
    to_location = tx.to_location
    return TransactionHistoryItemResponse(
        id=tx.id,
        from_location_id=tx.from_location_id,
        to_location_id=tx.to_location_id,
        from_location_code=from_location.location_code if from_location else None,
        from_location_name=from_location.location_name if from_location else None,
        to_location_code=to_location.location_code if to_location else None,
        to_location_name=to_location.location_name if to_location else None,
        transaction_type=tx.transaction_type,
        item_stock_id=tx.item_stock_id,
        quantity=tx.quantity,
        created_by_id=tx.created_by_id,
        created_at=tx.created_at,
    )


def _to_order_brief(order) -> OrderBriefResponse:
    return OrderBriefResponse.model_validate(order)


def _ensure_refs(
    db: Session,
    *,
    from_location_id: int,
    to_location_id: int,
    item_stock_id: int,
) -> None:
    if not (
        db.query(Location)
        .filter(Location.id == from_location_id, Location.is_active.is_(True))
        .first()
    ):
        raise ValueError(f"From location id not found: {from_location_id}")
    if not (
        db.query(Location)
        .filter(Location.id == to_location_id, Location.is_active.is_(True))
        .first()
    ):
        raise ValueError(f"To location id not found: {to_location_id}")
    if not (
        db.query(ItemStock)
        .filter(ItemStock.id == item_stock_id, ItemStock.is_active.is_(True))
        .first()
    ):
        raise ValueError(f"Item stock id not found: {item_stock_id}")


def list_transactions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    item_stock_id: Optional[int] = None,
    from_location_id: Optional[int] = None,
    to_location_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
) -> TransactionListResponse:
    query = db.query(Transaction)
    if item_stock_id is not None:
        query = query.filter(Transaction.item_stock_id == item_stock_id)
    if from_location_id is not None:
        query = query.filter(Transaction.from_location_id == from_location_id)
    if to_location_id is not None:
        query = query.filter(Transaction.to_location_id == to_location_id)
    if transaction_type is not None:
        query = query.filter(Transaction.transaction_type == transaction_type)
    total = query.count()
    items = (
        query.order_by(Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_transaction_by_id(db: Session, transaction_id: int) -> Optional[Transaction]:
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def create_transaction(
    db: Session, body: TransactionCreate, created_by_id: int
) -> Transaction:
    """Insert ledger row only; does not mutate ItemStock."""
    _ensure_refs(
        db,
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        item_stock_id=body.item_stock_id,
    )
    tx = Transaction(
        from_location_id=body.from_location_id,
        to_location_id=body.to_location_id,
        transaction_type=body.transaction_type.strip(),
        item_stock_id=body.item_stock_id,
        quantity=body.quantity,
        created_by_id=created_by_id,
    )
    try:
        db.add(tx)
        db.commit()
        db.refresh(tx)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return tx


def create_history(db: Session, body: HistoryCreate, created_by_id: int) -> History:
    history = History(
        inbound_order_id=body.inbound_order_id,
        outbound_order_id=body.outbound_order_id,
        old_status=body.old_status,
        new_status=body.new_status,
        description=body.description,
        details=body.details,
        created_by_id=created_by_id,
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history

def get_history_by_id(db: Session, history_id: int) -> Optional[History]:
    return db.query(History).filter(History.id == history_id).first()

def list_histories(db: Session, page: int = 1, page_size: int = 20, inbound_order_id: Optional[int] = None, outbound_order_id: Optional[int] = None) -> HistoryListResponse:
    query = db.query(History)
    if inbound_order_id is not None:
        query = query.filter(History.inbound_order_id == inbound_order_id)
    if outbound_order_id is not None:
        query = query.filter(History.outbound_order_id == outbound_order_id)
    total = query.count()
    items = query.order_by(History.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return HistoryListResponse(items=[HistoryResponse.model_validate(h) for h in items], total=total, page=page, page_size=page_size)

def get_transaction_history(
    db: Session,
    qr_code: str | None = None,
    order_code: str | None = None,
) -> TransactionHistoryLookupResponse:
    if qr_code:
        normalized_qr = qr_code.strip()
        if not normalized_qr:
            raise ValueError("qr_code is required")
        qr_record = (
            db.query(QR_Code).filter(QR_Code.code == normalized_qr).first()
        )
        if not qr_record or not qr_record.item_stock_id:
            raise ValueError("QR code not found or not linked to stock")
        stock = (
            db.query(ItemStock)
            .options(
                joinedload(ItemStock.location),
                joinedload(ItemStock.item),
                joinedload(ItemStock.unit),
            )
            .filter(ItemStock.id == qr_record.item_stock_id)
            .first()
        )
        if not stock:
            raise ValueError("Item stock not found")
        transactions = (
            db.query(Transaction)
            .options(
                joinedload(Transaction.from_location),
                joinedload(Transaction.to_location),
            )
            .filter(Transaction.item_stock_id == qr_record.item_stock_id)
            .order_by(Transaction.created_at.asc())
            .all()
        )
        return TransactionHistoryLookupResponse(
            lookup_type="qr_code",
            qr_code=normalized_qr,
            item_stock_id=qr_record.item_stock_id,
            item_stock=_to_item_stock_lookup(stock),
            transactions=[_to_transaction_history_item(tx) for tx in transactions],
        )

    if order_code is not None:
        normalized_code = order_code.strip()
        if not normalized_code:
            raise ValueError("order_code is required")
        inbound = (
            db.query(InboundOrder)
            .filter(InboundOrder.order_code == normalized_code)
            .first()
        )
        outbound = (
            db.query(OutboundOrder)
            .filter(OutboundOrder.order_code == normalized_code)
            .first()
        )
        if not inbound and not outbound:
            raise ValueError("Order not found")
        q = db.query(History)
        if inbound:
            q = q.filter(History.inbound_order_id == inbound.id)
            order_type = "inbound"
            order_meta = _to_order_brief(inbound)
        else:
            q = q.filter(History.outbound_order_id == outbound.id)
            order_type = "outbound"
            order_meta = _to_order_brief(outbound)
        histories = q.order_by(History.created_at.asc()).all()
        return TransactionHistoryLookupResponse(
            lookup_type="order",
            order_code=normalized_code,
            order_type=order_type,
            order=order_meta,
            histories=[
                HistoryResponse.model_validate(history) for history in histories
            ],
        )

    raise ValueError("qr_code or order_code is required")