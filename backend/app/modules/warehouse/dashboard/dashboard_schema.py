from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

StockAgingBucketKey = Literal["lte_30", "days_31_60", "gt_60"]


class ReportKpiResponse(BaseModel):
    total_inbound_orders: int = 0
    total_outbound_orders: int = 0
    total_inventory_value: Decimal = Decimal(0)
    unsolved_notifications: int = 0
    active_carts_count: int = 0
    in_transit_amr_count: int = 0
    queued_requests_count: int = 0
    parts_completed_today: int = 0


class ReportTrendPoint(BaseModel):
    label: str
    period_start: date
    period_end: date
    inbound_orders: int
    outbound_orders: int
    inventory_quantity: Decimal
    inventory_value: Decimal


class ReportTrendResponse(BaseModel):
    granularity: Literal["day", "week"]
    points: list[ReportTrendPoint]


class TopProductRow(BaseModel):
    item_id: int
    label: str
    total_quantity: int


class ReportTopProductsResponse(BaseModel):
    period: Literal["week", "month"]
    inbound_top: list[TopProductRow]
    outbound_top: list[TopProductRow]
    stock_top: list[TopProductRow]


class StockAgingBucketSummary(BaseModel):
    key: StockAgingBucketKey
    label: str
    total_quantity: Decimal
    percent: float


class StockAgingRow(BaseModel):
    item_stock_id: int
    sku: str
    quantity: Decimal
    lot: str | None
    created_at: datetime
    holding_days: int


class ReportStockAgingOverviewResponse(BaseModel):
    buckets: list[StockAgingBucketSummary]
    longest_holding: list[StockAgingRow]


class ReportStockAgingBucketResponse(BaseModel):
    bucket: StockAgingBucketKey
    items: list[StockAgingRow]
