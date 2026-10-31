# Production Station & Machine Domain (7)

> 73 nodes · cohesion 0.07

## Key Concepts

- **machine_service.py** (23 connections) — `backend/app/modules/production/machine_service.py`
- **station_api.py** (23 connections) — `backend/app/modules/production/station_api.py`
- **station_service.py** (23 connections) — `backend/app/modules/production/station_service.py`
- **machine_api.py** (21 connections) — `backend/app/modules/production/machine_api.py`
- **location_guard.py** (17 connections) — `backend/app/modules/production/location_guard.py`
- **ensure_location_has_no_stock()** (14 connections) — `backend/app/modules/production/location_guard.py`
- **release_location()** (11 connections) — `backend/app/modules/production/location_guard.py`
- **create_machine()** (11 connections) — `backend/app/modules/production/machine_service.py`
- **update_machine()** (11 connections) — `backend/app/modules/production/machine_service.py`
- **station_schema.py** (11 connections) — `backend/app/modules/production/station_schema.py`
- **find_map_node()** (10 connections) — `backend/app/modules/production/location_guard.py`
- **machine_schema.py** (10 connections) — `backend/app/modules/production/machine_schema.py`
- **AvailableMachineResponse** (9 connections) — `backend/app/modules/production/machine_schema.py`
- **StationCatalogItem** (9 connections) — `backend/app/modules/production/station_schema.py`
- **get_station_catalog()** (9 connections) — `backend/app/modules/production/station_service.py`
- **update_station_slot()** (9 connections) — `backend/app/modules/production/station_service.py`
- **MachineSlotInfo** (8 connections) — `backend/app/modules/production/machine_schema.py`
- **create_station_slot()** (8 connections) — `backend/app/modules/production/station_service.py`
- **resolve_warehouse_id()** (7 connections) — `backend/app/modules/production/location_guard.py`
- **create_machine()** (7 connections) — `backend/app/modules/production/machine_api.py`
- **update_machine()** (7 connections) — `backend/app/modules/production/machine_api.py`
- **MachineCreateRequest** (7 connections) — `backend/app/modules/production/machine_schema.py`
- **MachineUpdateRequest** (7 connections) — `backend/app/modules/production/machine_schema.py`
- **delete_machine()** (7 connections) — `backend/app/modules/production/machine_service.py`
- **list_available_machines()** (7 connections) — `backend/app/modules/production/machine_service.py`
- *... and 48 more nodes in this community*

## Relationships

- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (19 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (15 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (12 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (11 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (6 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (5 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (2 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (2 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (2 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (2 shared connections)

## Source Files

- `backend/app/modules/production/location_guard.py`
- `backend/app/modules/production/machine_api.py`
- `backend/app/modules/production/machine_schema.py`
- `backend/app/modules/production/machine_service.py`
- `backend/app/modules/production/station_api.py`
- `backend/app/modules/production/station_schema.py`
- `backend/app/modules/production/station_service.py`

## Audit Trail

- EXTRACTED: 242 (90%)
- INFERRED: 26 (10%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*