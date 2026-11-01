# Production Dispatch & AMR Flow (42)

> 37 nodes · cohesion 0.09

## Key Concepts

- **Location** (115 connections) — `backend/app/modules/warehouse/location_map/location_model.py`
- **Session** (25 connections)
- **sync_locations_from_map()** (16 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **update_location()** (9 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **get_location_by_id()** (8 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **LocationUpdate** (7 connections) — `backend/app/modules/warehouse/location_map/location_schema.py`
- **_ensure_warehouse_and_zone()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **get_zone_map_layout()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **list_locations()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_location_query()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **upsert_location()** (7 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **update_location()** (6 connections) — `backend/app/modules/warehouse/location_map/location_api.py`
- **delete_location()** (6 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **.calculate_distance()** (5 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **_apply_shelf_to_location()** (5 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_assign_node_numbers()** (5 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_move_location_references()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_orphan_lookup()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_reference_counts_by_location()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_resolve_or_create_machine()** (4 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **.calculate_distance()** (3 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **_dedupe_shelves()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_match_shelf_to_location()** (3 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **_blocked_message()** (2 connections) — `backend/app/modules/warehouse/location_map/location_service.py`
- **2D Euclidean distance between two map nodes.** (1 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- *... and 12 more nodes in this community*

## Relationships

- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (32 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (19 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (15 shared connections)
- [Production Station & Machine Domain (7)](Production_Station_&_Machine_Domain_7.md) (12 shared connections)
- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (11 shared connections)
- [Warehouse Location & Storage (57)](Warehouse_Location_&_Storage_57.md) (11 shared connections)
- [Warehouse Location & Storage (63)](Warehouse_Location_&_Storage_63.md) (9 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (6 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (5 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (4 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (4 shared connections)

## Source Files

- `backend/app/modules/production/dispatch/__init__.py`
- `backend/app/modules/production/dispatch/cart_selector.py`
- `backend/app/modules/warehouse/location_map/location_api.py`
- `backend/app/modules/warehouse/location_map/location_model.py`
- `backend/app/modules/warehouse/location_map/location_schema.py`
- `backend/app/modules/warehouse/location_map/location_service.py`

## Audit Trail

- EXTRACTED: 145 (66%)
- INFERRED: 74 (34%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*