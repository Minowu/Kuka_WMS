# Production Dispatch & AMR Flow (5)

> 78 nodes · cohesion 0.05

## Key Concepts

- **database.py** (52 connections) — `backend/app/core/database.py`
- **db_session()** (35 connections) — `backend/app/core/database.py`
- **datetime** (33 connections)
- **logger.py** (31 connections) — `backend/app/core/logger.py`
- **kuka_fleet_client.py** (28 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **production_celery_task.py** (27 connections) — `backend/app/modules/production/production_celery_task.py`
- **ws_manager.py** (25 connections) — `backend/app/socket/ws_manager.py`
- **get_logger()** (24 connections) — `backend/app/core/logger.py`
- **config.py** (21 connections) — `backend/app/core/config.py`
- **webhook_handler.py** (21 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **event_bus.py** (21 connections) — `backend/app/socket/event_bus.py`
- **celery_app.py** (18 connections) — `backend/app/core/celery_app.py`
- **resolve_location_recipient_user_ids()** (17 connections) — `backend/app/socket/event_bus.py`
- **fail_and_release()** (15 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **submit_fleet_task()** (12 connections) — `backend/app/modules/production/production_celery_task.py`
- **dashboard_celery_task.py** (8 connections) — `backend/app/modules/warehouse/dashboard/dashboard_celery_task.py`
- **notification_celery_task.py** (8 connections) — `backend/app/modules/warehouse/notificcation/notification_celery_task.py`
- **schedule_event_after_commit()** (8 connections) — `backend/app/socket/event_bus.py`
- **_authenticate_ws_token()** (8 connections) — `backend/app/socket/ws_manager.py`
- **websocket_endpoint()** (8 connections) — `backend/app/socket/ws_manager.py`
- **robot_api.py** (8 connections) — `backend/legacy_wms_archive/robot/robot_api.py`
- **setup_logger()** (7 connections) — `backend/app/core/logger.py`
- **sweep_fleet_tasks()** (7 connections) — `backend/app/modules/production/production_celery_task.py`
- **robot_celery_task.py** (7 connections) — `backend/legacy_wms_archive/robot/robot_celery_task.py`
- **_flush_ws_events_after_commit()** (6 connections) — `backend/app/socket/event_bus.py`
- *... and 53 more nodes in this community*

## Relationships

- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (46 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (20 shared connections)
- [Celery Asynchronous Tasks (96)](Celery_Asynchronous_Tasks_96.md) (14 shared connections)
- [Frontend API & Data Services (26)](Frontend_API_&_Data_Services_26.md) (12 shared connections)
- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (12 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (10 shared connections)
- [Warehouse Domain (36)](Warehouse_Domain_36.md) (10 shared connections)
- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (10 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (9 shared connections)
- [Production Dispatch & AMR Flow (19)](Production_Dispatch_&_AMR_Flow_19.md) (9 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (7 shared connections)
- [Main Module (109)](Main_Module_109.md) (7 shared connections)

## Source Files

- `backend/app/core/celery_app.py`
- `backend/app/core/config.py`
- `backend/app/core/database.py`
- `backend/app/core/logger.py`
- `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- `backend/app/modules/production/dispatch/webhook_handler.py`
- `backend/app/modules/production/production_celery_task.py`
- `backend/app/modules/warehouse/dashboard/dashboard_celery_task.py`
- `backend/app/modules/warehouse/notificcation/notification_celery_task.py`
- `backend/app/socket/event_bus.py`
- `backend/app/socket/ws_manager.py`
- `backend/legacy_wms_archive/robot/robot_api.py`
- `backend/legacy_wms_archive/robot/robot_celery_task.py`

## Audit Trail

- EXTRACTED: 389 (97%)
- INFERRED: 14 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*