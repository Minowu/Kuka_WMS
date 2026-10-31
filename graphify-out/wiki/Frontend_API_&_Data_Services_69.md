# Frontend API & Data Services (69)

> 25 nodes · cohesion 0.16

## Key Concepts

- **outbound_order_api.py** (28 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **DbSession** (14 connections)
- **update_outbound_order()** (9 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **create_outbound_order()** (8 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **get** (6 connections)
- **post** (6 connections)
- **app_modules_robot_robot_service** (5 connections)
- **calculate_outbound_order()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **confirm_outbound_order_no_qr()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **confirm_outbound_order_qr()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **execute_outbound_qr_manual()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **execute_outbound_task()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **get_outbound_order_by_id()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **list_outbound_orders()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **delete_outbound_order()** (4 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **get_outbound_lacked_details()** (4 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **get_outbound_manual_allocation_tasks()** (4 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **get_outbound_order_details()** (4 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **get_outbound_robot_tasks()** (4 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`
- **Depends** (2 connections)
- **app_modules_warehouse_outbound_order_outbound_celery_task** (1 connections)
- **delete** (1 connections)
- **patch** (1 connections)
- **_OUTBOUND_CREATE** (1 connections)
- **_OUTBOUND_UPDATE** (1 connections)

## Relationships

- [Outbound Order Schema Module (65)](Outbound_Order_Schema_Module_65.md) (15 shared connections)
- [Celery Asynchronous Tasks (96)](Celery_Asynchronous_Tasks_96.md) (11 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (3 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (3 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (3 shared connections)
- [Frontend API & Data Services (26)](Frontend_API_&_Data_Services_26.md) (1 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (1 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (1 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (1 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (1 shared connections)
- [Main Module (109)](Main_Module_109.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/outbound_order/outbound_order_api.py`

## Audit Trail

- EXTRACTED: 64 (71%)
- INFERRED: 26 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*