from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, func, table, select, exists, case, and_, column
from sqlalchemy.orm import relationship, column_property

from app.core.database import Base


_stocktake_item_tbl = table(
    "stocktake_item",
    column("stocktake_id", Integer),
    column("status", String),
)

def _stocktake_item_exists(stocktake_id_col, *criteria):
    return exists(
        select(1)
        .where(
            _stocktake_item_tbl.c.stocktake_id == stocktake_id_col,
            *criteria,
        )
        .correlate_except(_stocktake_item_tbl)
    )


def _stocktake_has_any_item(stocktake_id_col):
    return _stocktake_item_exists(stocktake_id_col)


def _stocktake_has_item_status(stocktake_id_col, status_value: str):
    return _stocktake_item_exists(
        stocktake_id_col,
        _stocktake_item_tbl.c.status == status_value,
    )


def _stocktake_all_items_status(stocktake_id_col, status_value: str):
    return and_(
        _stocktake_item_exists(stocktake_id_col),
        ~_stocktake_item_exists(
            stocktake_id_col,
            _stocktake_item_tbl.c.status != status_value,
        ),
    )


class Stocktake(Base):
    __tablename__ = "stocktake"

    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    items = relationship(
        "StocktakeItemStock",
        back_populates="stocktake",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    status = column_property(
        case(
            (
                _stocktake_has_item_status(id, "discrepancy"),
                "discrepancy",
            ),
            (
                _stocktake_all_items_status(id, "completed"),
                "completed",
            ),
            (
                _stocktake_all_items_status(id, "initialize"),
                "initialize",
            ),
            (
                _stocktake_has_any_item(id),
                "in_progress",
            ),
            else_="initialize",
        )
    )


class StocktakeItemStock(Base):
    __tablename__ = "stocktake_item"

    id = Column(Integer, primary_key=True, index=True)
    stocktake_id = Column(
        Integer,
        ForeignKey("stocktake.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_stock_id = Column(Integer, ForeignKey("item_stock.id"), nullable=False, index=True)
    lot_number = Column(String(100), nullable=False)
    location_id = Column(Integer, ForeignKey("location.id"), nullable=False, index=True)
    desired_quantity = Column(Integer, nullable=False)
    actual_quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(String(100), nullable=False)

    stocktake = relationship(
        "Stocktake",
        back_populates="items",
        foreign_keys=[stocktake_id],
    )
    item_stock = relationship("ItemStock", foreign_keys=[item_stock_id], lazy="joined")
    location = relationship("Location", foreign_keys=[location_id], lazy="joined")
