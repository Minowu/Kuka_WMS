# Warehouse Domain (49)

> 32 nodes · cohesion 0.13

## Key Concepts

- **dashboard_api.py** (24 connections) — `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- **dashboard_trend_service.py** (19 connections) — `backend/app/modules/warehouse/dashboard/dashboard_trend_service.py`
- **dashboard_schema.py** (18 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **_ensure_warehouse_exists()** (12 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **get_report_trends()** (11 connections) — `backend/app/modules/warehouse/dashboard/dashboard_trend_service.py`
- **BaseModel** (9 connections)
- **get_report_top_products()** (6 connections) — `backend/app/modules/warehouse/dashboard/dashboard_top_products_service.py`
- **get_report_stock_aging_bucket()** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- **DbSession** (5 connections)
- **get** (5 connections)
- **ReportKpiResponse** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **ReportStockAgingBucketResponse** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **ReportStockAgingOverviewResponse** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **ReportTopProductsResponse** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **ReportTrendResponse** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **TopProductRow** (5 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **get_report_kpis()** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- **get_report_stock_aging_overview()** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- **get_report_top_products()** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- **get_report_trends()** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- **ReportTrendPoint** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **StockAgingBucketSummary** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **StockAgingRow** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- **_last_12_week_periods()** (4 connections) — `backend/app/modules/warehouse/dashboard/dashboard_trend_service.py`
- **_last_12_day_periods()** (3 connections) — `backend/app/modules/warehouse/dashboard/dashboard_trend_service.py`
- *... and 7 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (41 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (4 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (3 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (2 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/dashboard/__init__.py`
- `backend/app/modules/warehouse/dashboard/dashboard_api.py`
- `backend/app/modules/warehouse/dashboard/dashboard_schema.py`
- `backend/app/modules/warehouse/dashboard/dashboard_top_products_service.py`
- `backend/app/modules/warehouse/dashboard/dashboard_trend_service.py`
- `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`

## Audit Trail

- EXTRACTED: 124 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*