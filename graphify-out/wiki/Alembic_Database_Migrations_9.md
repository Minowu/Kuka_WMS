# Alembic Database Migrations (9)

> 63 nodes · cohesion 0.10

## Key Concepts

- **FleetTask** (49 connections) — `backend/app/modules/production/production_models.py`
- **production_models.py** (36 connections) — `backend/app/modules/production/production_models.py`
- **dispatch_core.py** (35 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **seed_production_core.py** (34 connections) — `backend/scripts/seed_production_core.py`
- **env.py** (33 connections) — `backend/alembic/env.py`
- **TransportRequest** (33 connections) — `backend/app/modules/production/production_models.py`
- **UserLocation** (31 connections) — `backend/app/modules/production/production_models.py`
- **Machine** (28 connections) — `backend/app/modules/production/production_models.py`
- **auth_model.py** (27 connections) — `backend/app/modules/auth/auth_model.py`
- **test_dispatch_engine.py** (26 connections) — `backend/scripts/test_dispatch_engine.py`
- **dispatch/__init__.py** (25 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **reset_clean_data.py** (24 connections) — `backend/scripts/reset_clean_data.py`
- **TransportQueue** (23 connections) — `backend/app/modules/production/production_models.py`
- **test_kuka_fleet_replay.py** (22 connections) — `backend/scripts/test_kuka_fleet_replay.py`
- **RouteStepMachine** (21 connections) — `backend/app/modules/production/production_models.py`
- **ProductionRecord** (20 connections) — `backend/app/modules/production/production_models.py`
- **cart_selector.py** (19 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **queue_service.py** (19 connections) — `backend/app/modules/production/dispatch/queue_service.py`
- **TaskStatus** (18 connections) — `backend/app/modules/production/production_models.py`
- **warehouse_model.py** (17 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_model.py`
- **seed_production_core()** (17 connections) — `backend/scripts/seed_production_core.py`
- **reset_clean_slate()** (15 connections) — `backend/scripts/reset_clean_data.py`
- **production/__init__.py** (14 connections) — `backend/app/modules/production/__init__.py`
- **FleetApiCall** (13 connections) — `backend/app/modules/production/production_models.py`
- **run_verification()** (13 connections) — `backend/scripts/test_dispatch_engine.py`
- *... and 38 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (73 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (46 shared connections)
- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (34 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (27 shared connections)
- [Production Routes & Operations (70)](Production_Routes_&_Operations_70.md) (27 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (22 shared connections)
- [Production Dispatch & AMR Flow (19)](Production_Dispatch_&_AMR_Flow_19.md) (22 shared connections)
- [Production Station & Machine Domain (7)](Production_Station_&_Machine_Domain_7.md) (19 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (15 shared connections)
- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (10 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (8 shared connections)
- [Production Dispatch & AMR Flow (116)](Production_Dispatch_&_AMR_Flow_116.md) (6 shared connections)

## Source Files

- `backend/alembic/env.py`
- `backend/app/modules/auth/auth_model.py`
- `backend/app/modules/production/__init__.py`
- `backend/app/modules/production/dispatch/__init__.py`
- `backend/app/modules/production/dispatch/cart_selector.py`
- `backend/app/modules/production/dispatch/dispatch_core.py`
- `backend/app/modules/production/dispatch/queue_service.py`
- `backend/app/modules/production/dispatch_service.py`
- `backend/app/modules/production/production_models.py`
- `backend/app/modules/warehouse/warehouse_zone/warehouse_model.py`
- `backend/scripts/reset_clean_data.py`
- `backend/scripts/seed_production_core.py`
- `backend/scripts/test_dispatch_engine.py`
- `backend/scripts/test_kuka_fleet_replay.py`

## Audit Trail

- EXTRACTED: 440 (82%)
- INFERRED: 94 (18%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*