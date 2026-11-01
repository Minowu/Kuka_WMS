# Production Routes & Operations (8)

> 64 nodes · cohesion 0.08

## Key Concepts

- **route_api.py** (73 connections) — `backend/app/modules/production/route_api.py`
- **route_schema.py** (40 connections) — `backend/app/modules/production/route_schema.py`
- **get_pda_cnc_stations()** (18 connections) — `backend/app/modules/production/route_api.py`
- **DbSession** (17 connections)
- **BaseModel** (17 connections)
- **CurrentUser** (16 connections)
- **get_pda_washing_slots()** (13 connections) — `backend/app/modules/production/route_api.py`
- **get_pda_raw_materials()** (10 connections) — `backend/app/modules/production/route_api.py`
- **_ensure_user_can_access_location()** (8 connections) — `backend/app/modules/production/route_api.py`
- **_get_recent_location_errors_batch()** (8 connections) — `backend/app/modules/production/route_api.py`
- **return_empty_cart_from_washing()** (8 connections) — `backend/app/modules/production/route_api.py`
- **call_material()** (7 connections) — `backend/app/modules/production/route_api.py`
- **complete_machining_stage()** (7 connections) — `backend/app/modules/production/route_api.py`
- **get_pda_models()** (7 connections) — `backend/app/modules/production/route_api.py`
- **get** (7 connections)
- **post** (7 connections)
- **register_rack_at_raw_material()** (7 connections) — `backend/app/modules/production/route_api.py`
- **ProductionRouteCreate** (7 connections) — `backend/app/modules/production/route_schema.py`
- **activate_production_route()** (6 connections) — `backend/app/modules/production/route_api.py`
- **create_production_route()** (6 connections) — `backend/app/modules/production/route_api.py`
- **get_user_locations()** (6 connections) — `backend/app/modules/production/route_api.py`
- **delete_production_route()** (5 connections) — `backend/app/modules/production/route_api.py`
- **get_production_route()** (5 connections) — `backend/app/modules/production/route_api.py`
- **_get_recent_location_error()** (5 connections) — `backend/app/modules/production/route_api.py`
- **list_production_routes()** (5 connections) — `backend/app/modules/production/route_api.py`
- *... and 39 more nodes in this community*

## Relationships

- [Production Routes & Operations (70)](Production_Routes_&_Operations_70.md) (30 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (22 shared connections)
- [Production Station & Machine Domain (7)](Production_Station_&_Machine_Domain_7.md) (15 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (11 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (10 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (4 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (3 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (2 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)

## Source Files

- `backend/app/modules/production/route_api.py`
- `backend/app/modules/production/route_schema.py`

## Audit Trail

- EXTRACTED: 220 (86%)
- INFERRED: 37 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*