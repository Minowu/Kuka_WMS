# Dependencies Module (92)

> 16 nodes · cohesion 0.17

## Key Concepts

- **dependencies.py** (30 connections) — `backend/app/core/dependencies.py`
- **get_db()** (20 connections) — `backend/app/core/database.py`
- **get_current_user()** (17 connections) — `backend/app/core/dependencies.py`
- **require_permission()** (15 connections) — `backend/app/core/dependencies.py`
- **get_dev_admin_user()** (10 connections) — `backend/app/core/dependencies.py`
- **decode_access_token()** (5 connections) — `backend/app/core/security.py`
- **require_role()** (3 connections) — `backend/app/core/dependencies.py`
- **Depends** (2 connections)
- **Session** (2 connections)
- **Dependency to get database session.** (1 connections) — `backend/app/core/database.py`
- **Temporary integration bypass: no Bearer token; always use active admin user.** (1 connections) — `backend/app/core/dependencies.py`
- **checker()** (1 connections) — `backend/app/core/dependencies.py`
- **role_checker()** (1 connections) — `backend/app/core/dependencies.py`
- **fastapi_security** (1 connections)
- **HTTPAuthorizationCredentials** (1 connections)
- **security** (1 connections)

## Relationships

- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (10 shared connections)
- [Production Station & Machine Domain (7)](Production_Station_&_Machine_Domain_7.md) (6 shared connections)
- [Frontend API & Data Services (26)](Frontend_API_&_Data_Services_26.md) (6 shared connections)
- [Frontend API & Data Services (76)](Frontend_API_&_Data_Services_76.md) (4 shared connections)
- [Warehouse Domain (14)](Warehouse_Domain_14.md) (4 shared connections)
- [Warehouse Location & Storage (57)](Warehouse_Location_&_Storage_57.md) (4 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (4 shared connections)
- [Frontend API & Data Services (97)](Frontend_API_&_Data_Services_97.md) (4 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (3 shared connections)
- [Warehouse Domain (49)](Warehouse_Domain_49.md) (3 shared connections)
- [Warehouse Domain (54)](Warehouse_Domain_54.md) (3 shared connections)

## Source Files

- `backend/app/core/database.py`
- `backend/app/core/dependencies.py`
- `backend/app/core/security.py`

## Audit Trail

- EXTRACTED: 83 (91%)
- INFERRED: 8 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*