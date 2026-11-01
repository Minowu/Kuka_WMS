# Frontend API & Data Services (79)

> 20 nodes · cohesion 0.16

## Key Concepts

- **DbSession** (10 connections)
- **_user_to_response()** (8 connections) — `backend/app/modules/auth/auth_api.py`
- **list_roles()** (6 connections) — `backend/app/modules/auth/auth_api.py`
- **list_staff_usernames()** (6 connections) — `backend/app/modules/auth/auth_api.py`
- **refresh_token()** (6 connections) — `backend/app/modules/auth/auth_api.py`
- **update_user()** (6 connections) — `backend/app/modules/auth/auth_api.py`
- **delete_user()** (5 connections) — `backend/app/modules/auth/auth_api.py`
- **get_me()** (5 connections) — `backend/app/modules/auth/auth_api.py`
- **get_user_by_id()** (5 connections) — `backend/app/modules/auth/auth_api.py`
- **login()** (5 connections) — `backend/app/modules/auth/auth_api.py`
- **get** (5 connections)
- **signup()** (5 connections) — `backend/app/modules/auth/auth_api.py`
- **list_users()** (4 connections) — `backend/app/modules/auth/auth_api.py`
- **CurrentUser** (4 connections)
- **post** (3 connections)
- **delete** (1 connections)
- **patch** (1 connections)
- **Session** (1 connections)
- **Username list for tablet assign-by picker (any logged-in user).** (1 connections) — `backend/app/modules/auth/auth_api.py`
- **Lấy danh sách các vai trò (roles) trong hệ thống.** (1 connections) — `backend/app/modules/auth/auth_api.py`

## Relationships

- [Frontend API & Data Services (76)](Frontend_API_&_Data_Services_76.md) (17 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (10 shared connections)
- [Authentication & User Access (102)](Authentication_&_User_Access_102.md) (1 shared connections)

## Source Files

- `backend/app/modules/auth/auth_api.py`

## Audit Trail

- EXTRACTED: 50 (86%)
- INFERRED: 8 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*