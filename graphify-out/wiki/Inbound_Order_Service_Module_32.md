# Inbound Order Service Module (32)

> 43 nodes · cohesion 0.14

## Key Concepts

- **inbound_order_service.py** (60 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **Session** (21 connections)
- **InboundOrderDetail** (17 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_model.py`
- **History** (16 connections) — `backend/legacy_wms_archive/transaction_history/history_model.py`
- **_create_stock_and_allocation()** (14 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **execute_inbound_task()** (14 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **InboundOrder** (13 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_model.py`
- **cache_delete()** (12 connections) — `backend/app/core/cache.py`
- **InboundOrderAllocation** (10 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_model.py`
- **_clear_pending_cache_for_qr()** (10 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **create_inbound_order()** (10 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_purge_detail()** (10 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **update_inbound_order()** (10 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_create_inbound_order_qr_manual()** (10 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **caller_inbound_order()** (9 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **inbound_order_model.py** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_model.py`
- **_create_detail_with_stock_and_allocation()** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **get_inbound_order_detail()** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_upsert_allocations()** (8 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_delete_allocation()** (7 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_build_detail_response()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **delete_inbound_order()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_patch_detail()** (6 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_build_allocation_response()** (5 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- **_create_virtual_stock_relation()** (5 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- *... and 18 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (22 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (20 shared connections)
- [Inbound Order Schema Module (25)](Inbound_Order_Schema_Module_25.md) (16 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (9 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (8 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (4 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Frontend API & Data Services (26)](Frontend_API_&_Data_Services_26.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (2 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (2 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (2 shared connections)

## Source Files

- `backend/app/core/cache.py`
- `backend/legacy_wms_archive/inbound_order/inbound_order_model.py`
- `backend/legacy_wms_archive/inbound_order/inbound_order_service.py`
- `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- `backend/legacy_wms_archive/transaction_history/history_model.py`

## Audit Trail

- EXTRACTED: 149 (66%)
- INFERRED: 78 (34%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*