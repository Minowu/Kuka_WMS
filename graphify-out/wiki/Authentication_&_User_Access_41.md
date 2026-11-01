# Authentication & User Access (41)

> 37 nodes · cohesion 0.17

## Key Concepts

- **auth_service.py** (58 connections) — `backend/app/modules/auth/auth_service.py`
- **User** (54 connections) — `backend/app/modules/auth/auth_model.py`
- **Session** (21 connections)
- **Role** (16 connections) — `backend/app/modules/auth/auth_model.py`
- **sign_up()** (16 connections) — `backend/app/modules/auth/auth_service.py`
- **security.py** (14 connections) — `backend/app/core/security.py`
- **_user_query()** (12 connections) — `backend/app/modules/auth/auth_service.py`
- **_apply_access_on_create()** (10 connections) — `backend/app/modules/auth/auth_service.py`
- **login()** (10 connections) — `backend/app/modules/auth/auth_service.py`
- **update_user()** (9 connections) — `backend/app/modules/auth/auth_service.py`
- **_apply_access_on_update()** (8 connections) — `backend/app/modules/auth/auth_service.py`
- **delete_user()** (7 connections) — `backend/app/modules/auth/auth_service.py`
- **list_staff_usernames()** (7 connections) — `backend/app/modules/auth/auth_service.py`
- **list_users()** (7 connections) — `backend/app/modules/auth/auth_service.py`
- **create_access_token()** (6 connections) — `backend/app/core/security.py`
- **get_password_hash()** (6 connections) — `backend/app/core/security.py`
- **_assign_admin_access()** (6 connections) — `backend/app/modules/auth/auth_service.py`
- **authenticate_user()** (6 connections) — `backend/app/modules/auth/auth_service.py`
- **_ensure_admin_role_with_wildcard()** (6 connections) — `backend/app/modules/auth/auth_service.py`
- **_get_active_user_by_email()** (6 connections) — `backend/app/modules/auth/auth_service.py`
- **_get_roles_by_ids()** (6 connections) — `backend/app/modules/auth/auth_service.py`
- **refresh_access_token()** (6 connections) — `backend/app/modules/auth/auth_service.py`
- **create_refresh_token()** (5 connections) — `backend/app/core/security.py`
- **_get_active_user_by_username()** (5 connections) — `backend/app/modules/auth/auth_service.py`
- **get_user_by_id()** (5 connections) — `backend/app/modules/auth/auth_service.py`
- *... and 12 more nodes in this community*

## Relationships

- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (27 shared connections)
- [Frontend API & Data Services (76)](Frontend_API_&_Data_Services_76.md) (24 shared connections)
- [Authentication & User Access (102)](Authentication_&_User_Access_102.md) (12 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (10 shared connections)
- [Frontend API & Data Services (79)](Frontend_API_&_Data_Services_79.md) (10 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (7 shared connections)
- [Frontend API & Data Services (26)](Frontend_API_&_Data_Services_26.md) (4 shared connections)
- [Frontend API & Data Services (69)](Frontend_API_&_Data_Services_69.md) (3 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (3 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Production Station & Machine Domain (7)](Production_Station_&_Machine_Domain_7.md) (2 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (2 shared connections)

## Source Files

- `backend/app/core/security.py`
- `backend/app/modules/auth/auth_model.py`
- `backend/app/modules/auth/auth_service.py`

## Audit Trail

- EXTRACTED: 175 (77%)
- INFERRED: 52 (23%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*