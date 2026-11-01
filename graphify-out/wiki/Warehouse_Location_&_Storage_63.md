# Warehouse Location & Storage (63)

> 27 nodes · cohesion 0.10

## Key Concepts

- **WarehouseMap** (11 connections) — `backend/app/modules/warehouse/location_map/location_model.py`
- **import_warehouse_map()** (10 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **get_map_data()** (9 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **extract_shelf_nodes_from_zip()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **preview_warehouse_map_import()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **MapDataResponse** (6 connections) — `backend/app/modules/warehouse/location_map/location_schema.py`
- **create_map_metadata()** (6 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **move_assigned_stock_cache()** (6 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **MapCreate** (5 connections) — `backend/app/modules/warehouse/location_map/location_schema.py`
- **export_warehouse_map()** (5 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **adapt_kuka_floor_map_to_canvas()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_load_compress_json()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_read_map_raw_content()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **resolve_map_zip_path()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_extract_shelves_from_kuka_floor_map()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_is_kuka_floor_map()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **Path** (3 connections)
- **_save_uploaded_zip()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **Base** (2 connections)
- **UploadFile** (2 connections)
- **.machine_code()** (1 connections) — `backend/app/modules/warehouse/location_map/location_model.py`
- **.zone_id()** (1 connections) — `backend/app/modules/warehouse/location_map/location_model.py`
- **Detect and parse either raw JSON or ZIP archive containing map data.** (1 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **Extract location nodes from new KUKA floor format for synchronizing database…** (1 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **Transform KUKA floorList map (meters) into standard 2D canvas MapDataResponse…** (1 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- *... and 2 more nodes in this community*

## Relationships

- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (18 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (9 shared connections)
- [Warehouse Location & Storage (57)](Warehouse_Location_&_Storage_57.md) (5 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (4 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (3 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (2 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/location_map/location_model.py`
- `backend/app/modules/warehouse/location_map/location_schema.py`
- `backend/app/modules/warehouse/location_map/location_service.py`

## Audit Trail

- EXTRACTED: 73 (95%)
- INFERRED: 4 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*