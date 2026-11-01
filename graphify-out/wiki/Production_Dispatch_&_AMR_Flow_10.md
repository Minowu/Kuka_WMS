# Production Dispatch & AMR Flow (10)

> 63 nodes · cohesion 0.08

## Key Concepts

- **ItemStock** (110 connections) — `backend/app/modules/warehouse/item_stock/item_stock_model.py`
- **Item** (59 connections) — `backend/app/modules/warehouse/item/item_model.py`
- **sqlalchemy_orm** (59 connections)
- **location_model.py** (40 connections) — `backend/app/modules/warehouse/location_map/location_model.py`
- **item_stock_model.py** (37 connections) — `backend/app/modules/warehouse/item_stock/item_stock_model.py`
- **item_model.py** (32 connections) — `backend/app/modules/warehouse/item/item_model.py`
- **dashboard_stock_aging_service.py** (31 connections) — `backend/app/modules/warehouse/dashboard/dashboard_stock_aging_service.py`
- **dashboard_snapshot_service.py** (25 connections) — `backend/app/modules/warehouse/dashboard/dashboard_snapshot_service.py`
- **test_cart_selector_same_machine.py** (23 connections) — `backend/tests/test_cart_selector_same_machine.py`
- **dashboard_service.py** (22 connections) — `backend/app/modules/warehouse/dashboard/dashboard_service.py`
- **dashboard_top_products_service.py** (21 connections) — `backend/app/modules/warehouse/dashboard/dashboard_top_products_service.py`
- **countable_stock_level_criterion()** (14 connections) — `backend/app/modules/warehouse/item_stock/item_stock_model.py`
- **get_report_stock_aging_overview()** (13 connections) — `backend/app/modules/warehouse/dashboard/dashboard_stock_aging_service.py`
- **get_report_kpis()** (12 connections) — `backend/app/modules/warehouse/dashboard/dashboard_service.py`
- **get_report_stock_aging_bucket()** (12 connections) — `backend/app/modules/warehouse/dashboard/dashboard_stock_aging_service.py`
- **positive_stock_quantity_criterion()** (12 connections) — `backend/app/modules/warehouse/item_stock/item_stock_model.py`
- **.find_fifo_available_cart()** (11 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **compute_live_total_inventory_value()** (11 connections) — `backend/app/modules/warehouse/dashboard/dashboard_snapshot_service.py`
- **TestCartSelectorSameMachine** (11 connections) — `backend/tests/test_cart_selector_same_machine.py`
- **_storage_stock_filters()** (10 connections) — `backend/app/modules/warehouse/dashboard/dashboard_snapshot_service.py`
- **compute_live_total_quantity()** (9 connections) — `backend/app/modules/warehouse/dashboard/dashboard_snapshot_service.py`
- **_top_stock()** (9 connections) — `backend/app/modules/warehouse/dashboard/dashboard_top_products_service.py`
- **vn_today()** (8 connections) — `backend/app/modules/warehouse/dashboard/dashboard_snapshot_service.py`
- **_to_row()** (8 connections) — `backend/app/modules/warehouse/dashboard/dashboard_stock_aging_service.py`
- **_base_filters()** (7 connections) — `backend/app/modules/warehouse/dashboard/dashboard_stock_aging_service.py`
- *... and 38 more nodes in this community*

## Relationships

- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (73 shared connections)
- [Warehouse Domain (49)](Warehouse_Domain_49.md) (41 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (22 shared connections)
- [Warehouse Domain (14)](Warehouse_Domain_14.md) (22 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (20 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (19 shared connections)
- [Warehouse Domain (54)](Warehouse_Domain_54.md) (18 shared connections)
- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (14 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (13 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (13 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (11 shared connections)
- [Production Routes & Operations (70)](Production_Routes_&_Operations_70.md) (11 shared connections)

## Source Files

- `backend/app/modules/production/dispatch/cart_selector.py`
- `backend/app/modules/warehouse/dashboard/dashboard_service.py`
- `backend/app/modules/warehouse/dashboard/dashboard_snapshot_service.py`
- `backend/app/modules/warehouse/dashboard/dashboard_stock_aging_service.py`
- `backend/app/modules/warehouse/dashboard/dashboard_top_products_service.py`
- `backend/app/modules/warehouse/item/item_model.py`
- `backend/app/modules/warehouse/item_stock/item_stock_model.py`
- `backend/app/modules/warehouse/location_map/location_model.py`
- `backend/legacy_wms_archive/transaction_history/history_model.py`
- `backend/tests/test_cart_selector_same_machine.py`

## Audit Trail

- EXTRACTED: 416 (78%)
- INFERRED: 116 (22%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*