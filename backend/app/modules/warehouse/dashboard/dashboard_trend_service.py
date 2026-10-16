"""Report trend aggregation (12 days / 12 weeks) decoupled for CNC AMR architecture."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy.orm import Session

from app.modules.warehouse.dashboard.dashboard_schema import (
    ReportTrendPoint,
    ReportTrendResponse,
)
from app.modules.warehouse.dashboard.dashboard_snapshot_service import (
    compute_live_total_inventory_value,
    compute_live_total_quantity,
    vn_today,
)
from app.modules.warehouse.warehouse_zone.warehouse_service import _ensure_warehouse_exists

VN_TIMEZONE = "Asia/Ho_Chi_Minh"


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _last_12_day_periods(today: date) -> list[tuple[date, date, str]]:
    periods: list[tuple[date, date, str]] = []
    for offset in range(11, -1, -1):
        d = today - timedelta(days=offset)
        periods.append((d, d, d.strftime("%d/%m")))
    return periods


def _last_12_week_periods(today: date) -> list[tuple[date, date, str]]:
    current_week_start = _week_start(today)
    periods: list[tuple[date, date, str]] = []
    for weeks_ago in range(11, -1, -1):
        start = current_week_start - timedelta(weeks=weeks_ago)
        end = today if weeks_ago == 0 else start + timedelta(days=6)
        periods.append((start, end, f"Tuần {start.strftime('%d/%m')}"))
    return periods


def get_report_trends(
    db: Session,
    *,
    warehouse_id: int,
    granularity: Literal["day", "week"],
) -> ReportTrendResponse:
    _ensure_warehouse_exists(db, warehouse_id)
    today = vn_today()

    if granularity == "day":
        periods = _last_12_day_periods(today)
    else:
        periods = _last_12_week_periods(today)

    live_qty = compute_live_total_quantity(db, warehouse_id)
    live_value = compute_live_total_inventory_value(db, warehouse_id)

    points: list[ReportTrendPoint] = []
    for period_start, period_end, label in periods:
        is_current = (period_start <= today <= period_end)
        points.append(
            ReportTrendPoint(
                label=label,
                period_start=period_start,
                period_end=period_end,
                inbound_orders=0,
                outbound_orders=0,
                inventory_quantity=live_qty if is_current else Decimal("0"),
                inventory_value=live_value if is_current else Decimal("0"),
            )
        )

    return ReportTrendResponse(granularity=granularity, points=points)
