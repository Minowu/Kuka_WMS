# Warehouse Location & Storage (62)

> 27 nodes · cohesion 0.12

## Key Concepts

- **location_service.py** (102 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **list_locations_for_map()** (16 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **get_location_detail()** (10 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **generate_qr_location_code()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **list_locations_for_zone_map()** (6 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **LocationDetailResponse** (5 connections) — `backend/app/modules/warehouse/location_map/location_schema.py`
- **LocationDetailStockItem** (5 connections) — `backend/app/modules/warehouse/location_map/location_schema.py`
- **_active_stock_totals()** (5 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_assigned_stocks_for_location()** (5 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **warehouse_mode.py** (4 connections) — `backend/app/core/warehouse_mode.py`
- **is_manual_warehouse()** (4 connections) — `backend/app/core/warehouse_mode.py`
- **LocationDetailSummary** (4 connections) — `backend/app/modules/warehouse/location_map/location_schema.py`
- **_use_manual_storage_90mm_label()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **location_ids_with_assigned_qr()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **parse_shelf_node_from_map_node()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **render_location_qr_codes()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_shelf_may_take_location()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_location_labels_per_page()** (2 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **overlay_status_with_assign_cache()** (2 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **ParsedShelfNode** (2 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **Decimal** (2 connections)
- **_vcc_logo_data_uri()** (2 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **Warehouse operation mode helpers (manual vs auto).** (1 connections) — `backend/app/core/warehouse_mode.py`
- **Manual warehouses use compact QR-only labels; auto warehouses use full Bacviet…** (1 connections) — `backend/app/core/warehouse_mode.py`
- **Fallback to warehouse map after Zone table removal.** (1 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- *... and 2 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (32 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (19 shared connections)
- [Warehouse Location & Storage (63)](Warehouse_Location_&_Storage_63.md) (18 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (10 shared connections)
- [Warehouse Location & Storage (57)](Warehouse_Location_&_Storage_57.md) (9 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (8 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (6 shared connections)
- [Mock Print Export Module (21)](Mock_Print_Export_Module_21.md) (4 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (3 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (2 shared connections)

## Source Files

- `backend/app/core/warehouse_mode.py`
- `backend/app/modules/warehouse/location_map/location_schema.py`
- `backend/app/modules/warehouse/location_map/location_service.py`

## Audit Trail

- EXTRACTED: 152 (94%)
- INFERRED: 10 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*