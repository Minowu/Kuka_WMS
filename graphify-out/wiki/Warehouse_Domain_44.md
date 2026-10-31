# Warehouse Domain (44)

> 35 nodes · cohesion 0.13

## Key Concepts

- **notification_api.py** (22 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **notification_service.py** (20 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **notification_schema.py** (9 connections) — `backend/app/modules/warehouse/notificcation/notification_schema.py`
- **Session** (9 connections)
- **NotificationResponse** (7 connections) — `backend/app/modules/warehouse/notificcation/notification_schema.py`
- **create_notification()** (6 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **DbSession** (6 connections)
- **update_notification()** (6 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **NotificationCreate** (6 connections) — `backend/app/modules/warehouse/notificcation/notification_schema.py`
- **NotificationUpdate** (6 connections) — `backend/app/modules/warehouse/notificcation/notification_schema.py`
- **Any** (6 connections)
- **get_notification()** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **resolve_notification()** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **NotificationListResponse** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_schema.py`
- **check_and_create_notifications_under_over_min_max()** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **create_notification()** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **list_notifications()** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **update_notification()** (5 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **delete_notification()** (4 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **list_notifications()** (4 connections) — `backend/app/modules/warehouse/notificcation/notification_api.py`
- **BaseModel** (4 connections)
- **check_long_holding_stock()** (4 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **count_unsolved_notifications()** (4 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **get_notification_by_id()** (4 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- **resolve_notification()** (4 connections) — `backend/app/modules/warehouse/notificcation/notification_service.py`
- *... and 10 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (5 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (5 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (3 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (3 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/notificcation/__init__.py`
- `backend/app/modules/warehouse/notificcation/notification_api.py`
- `backend/app/modules/warehouse/notificcation/notification_schema.py`
- `backend/app/modules/warehouse/notificcation/notification_service.py`

## Audit Trail

- EXTRACTED: 94 (92%)
- INFERRED: 8 (8%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*