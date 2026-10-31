# Celery Asynchronous Tasks (96)

> 15 nodes · cohesion 0.36

## Key Concepts

- **outbound_celery_task.py** (19 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **_dump()** (10 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **Any** (9 connections)
- **task** (9 connections)
- **calculate_outbound_order_task()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **create_outbound_order_task()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **update_outbound_order_task()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **get_outbound_lacked_details_task()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **get_outbound_manual_allocation_tasks_task()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **get_outbound_order_by_id_task()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **get_outbound_order_details_task()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **get_outbound_robot_tasks_task()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **execute_outbound_task_task()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`
- **app_modules_warehouse_outbound_order_outbound_order_schema** (3 connections)
- **app_modules_warehouse_outbound_order** (2 connections)

## Relationships

- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (14 shared connections)
- [Frontend API & Data Services (69)](Frontend_API_&_Data_Services_69.md) (11 shared connections)
- [Outbound Order Schema Module (65)](Outbound_Order_Schema_Module_65.md) (4 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (1 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (1 shared connections)
- [Frontend API & Data Services (26)](Frontend_API_&_Data_Services_26.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/outbound_order/outbound_celery_task.py`

## Audit Trail

- EXTRACTED: 57 (81%)
- INFERRED: 13 (19%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*