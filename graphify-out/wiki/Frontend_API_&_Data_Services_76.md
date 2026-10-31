# Frontend API & Data Services (76)

> 21 nodes · cohesion 0.22

## Key Concepts

- **auth_api.py** (41 connections) — `backend/app/modules/auth/auth_api.py`
- **auth_schema.py** (20 connections) — `backend/app/modules/auth/auth_schema.py`
- **BaseModel** (14 connections)
- **UserUpdate** (9 connections) — `backend/app/modules/auth/auth_schema.py`
- **UserCreate** (8 connections) — `backend/app/modules/auth/auth_schema.py`
- **UserResponse** (7 connections) — `backend/app/modules/auth/auth_schema.py`
- **LoginRequest** (6 connections) — `backend/app/modules/auth/auth_schema.py`
- **TokenResponse** (6 connections) — `backend/app/modules/auth/auth_schema.py`
- **LoginResponse** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **RoleBrief** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **StaffUsernamesResponse** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **UserAccessSummary** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **UserListResponse** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **UserSignupResponse** (5 connections) — `backend/app/modules/auth/auth_schema.py`
- **RefreshTokenRequest** (4 connections) — `backend/app/modules/auth/auth_schema.py`
- **RefreshTokenResponse** (4 connections) — `backend/app/modules/auth/auth_schema.py`
- **field_validator** (3 connections)
- **.passwords_match()** (2 connections) — `backend/app/modules/auth/auth_schema.py`
- **.empty_password_to_none()** (2 connections) — `backend/app/modules/auth/auth_schema.py`
- **.passwords_match()** (2 connections) — `backend/app/modules/auth/auth_schema.py`
- **Aggregated access profile for FE routing/UI — not raw RBAC permission codes. -…** (1 connections) — `backend/app/modules/auth/auth_schema.py`

## Relationships

- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (24 shared connections)
- [Frontend API & Data Services (79)](Frontend_API_&_Data_Services_79.md) (17 shared connections)
- [Authentication & User Access (102)](Authentication_&_User_Access_102.md) (11 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (4 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (1 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)

## Source Files

- `backend/app/modules/auth/auth_api.py`
- `backend/app/modules/auth/auth_schema.py`

## Audit Trail

- EXTRACTED: 101 (89%)
- INFERRED: 12 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*