# Frontend API & Data Services (26)

> 46 nodes · cohesion 0.11

## Key Concepts

- **inbound_order_api.py** (34 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **inbound_celery_task.py** (15 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **DbSession** (15 connections)
- **post** (13 connections)
- **create_inbound_order()** (9 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **update_inbound_order()** (9 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **manual_inbound_scan()** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **AssignOrGetItemStockResponse** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`
- **InboundOrderCreate** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`
- **caller_inbound_order_task()** (7 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **create_inbound_order_task()** (7 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **_dump()** (7 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **update_inbound_order_task()** (7 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **AssignOrGetItemStockRequest** (7 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`
- **accept_inbound_task_task()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **get_inbound_order_details_task()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- **Any** (6 connections)
- **_assign_or_get_item_stocks()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **caller_inbound_order()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **InboundOrderResponse** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`
- **task** (5 connections)
- **assign_or_get_item_stocks()** (5 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **assign_or_get_item_stocks_by_location()** (5 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **assign_packing_to_item()** (5 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- **cache_for_packing_user()** (5 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- *... and 21 more nodes in this community*

## Relationships

- [Inbound Order Schema Module (25)](Inbound_Order_Schema_Module_25.md) (24 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (12 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (6 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (4 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (1 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (1 shared connections)
- [Main Module (109)](Main_Module_109.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Frontend API & Data Services (69)](Frontend_API_&_Data_Services_69.md) (1 shared connections)
- [Celery Asynchronous Tasks (96)](Celery_Asynchronous_Tasks_96.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/inbound_order/inbound_celery_task.py`
- `backend/legacy_wms_archive/inbound_order/inbound_order_api.py`
- `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`

## Audit Trail

- EXTRACTED: 125 (75%)
- INFERRED: 42 (25%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*