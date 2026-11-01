# Authentication & User Access (102)

> 13 nodes · cohesion 0.27

## Key Concepts

- **auth_access.py** (20 connections) — `backend/app/modules/auth/auth_access.py`
- **user_to_response()** (12 connections) — `backend/app/modules/auth/auth_access.py`
- **build_user_access_summary()** (11 connections) — `backend/app/modules/auth/auth_access.py`
- **resolve_accessible_warehouses()** (6 connections) — `backend/app/modules/auth/auth_access.py`
- **resolve_user_modules()** (5 connections) — `backend/app/modules/auth/auth_access.py`
- **WarehouseBrief** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **Session** (3 connections)
- **resolve_warehouse_scope()** (3 connections) — `backend/app/modules/auth/auth_access.py`
- **user_is_admin()** (3 connections) — `backend/app/modules/auth/auth_access.py`
- **Resolve aggregated user access for FE (no raw permission codes).** (1 connections) — `backend/app/modules/auth/auth_access.py`
- **Tablet/work modules derived from module roles (not permission codes).** (1 connections) — `backend/app/modules/auth/auth_access.py`
- **ModuleName** (1 connections)
- **WarehouseScope** (1 connections)

## Relationships

- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (12 shared connections)
- [Frontend API & Data Services (76)](Frontend_API_&_Data_Services_76.md) (11 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (2 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Frontend API & Data Services (79)](Frontend_API_&_Data_Services_79.md) (1 shared connections)

## Source Files

- `backend/app/modules/auth/auth_access.py`
- `backend/app/modules/auth/auth_schema.py`

## Audit Trail

- EXTRACTED: 42 (82%)
- INFERRED: 9 (18%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*