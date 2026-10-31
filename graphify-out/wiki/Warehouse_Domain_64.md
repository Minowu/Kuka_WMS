# Warehouse Domain (64)

> 27 nodes · cohesion 0.19

## Key Concepts

- **Warehouse** (30 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_model.py`
- **warehouse_service.py** (25 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **warehouse_api.py** (21 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- **warehouse_schema.py** (8 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_schema.py`
- **WarehouseResponse** (8 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_schema.py`
- **delete_warehouse()** (8 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **create_warehouse()** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- **update_warehouse()** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- **WarehouseCreate** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_schema.py`
- **WarehouseUpdate** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_schema.py`
- **get_warehouse_by_id()** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **list_warehouses()** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **Session** (6 connections)
- **update_warehouse()** (6 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **get_warehouse()** (5 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- **DbSession** (5 connections)
- **WarehouseListResponse** (5 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_schema.py`
- **create_warehouse()** (5 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`
- **delete_warehouse()** (4 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- **list_warehouses()** (4 connections) — `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- **BaseModel** (4 connections)
- **get** (2 connections)
- **warehouse_zone/__init__.py** (1 connections) — `backend/app/modules/warehouse/warehouse_zone/__init__.py`
- **delete** (1 connections)
- **patch** (1 connections)
- *... and 2 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (10 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (5 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (4 shared connections)
- [Warehouse Domain (49)](Warehouse_Domain_49.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (3 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (3 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (2 shared connections)
- [Authentication & User Access (102)](Authentication_&_User_Access_102.md) (2 shared connections)
- [Production Station & Machine Domain (7)](Production_Station_&_Machine_Domain_7.md) (2 shared connections)
- [Warehouse Domain (14)](Warehouse_Domain_14.md) (2 shared connections)

## Source Files

- `backend/app/modules/warehouse/warehouse_zone/__init__.py`
- `backend/app/modules/warehouse/warehouse_zone/warehouse_api.py`
- `backend/app/modules/warehouse/warehouse_zone/warehouse_model.py`
- `backend/app/modules/warehouse/warehouse_zone/warehouse_schema.py`
- `backend/app/modules/warehouse/warehouse_zone/warehouse_service.py`

## Audit Trail

- EXTRACTED: 93 (78%)
- INFERRED: 26 (22%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*