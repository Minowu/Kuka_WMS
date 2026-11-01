# Outbound Order Service Module (27)

> 46 nodes · cohesion 0.14

## Key Concepts

- **outbound_order_service.py** (70 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **Session** (29 connections)
- **OutboundOrderAllocation** (21 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_model.py`
- **OutboundOrderDetail** (21 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_model.py`
- **OutboundOrder** (16 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_model.py`
- **uuid** (15 connections)
- **greedy_allocate_stocks_to_lines()** (13 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **execute_outbound_task()** (12 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **calculate_outbound_order()** (11 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **create_outbound_order()** (11 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_settle_outbound_stock()** (10 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **update_outbound_order()** (10 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_get_fixed_quantity()** (9 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **get_outbound_order_detail()** (9 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **lacked_details()** (9 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_validate_calculate_outbound_lines()** (9 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **confirm_outbound_order()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_enforce_pick_split_manual_details()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_execute_outbound_task_manual()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_resolve_execute_detail_type()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **summarize_manual_allocation_tasks()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **delete_outbound_order()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **execute_qr_manual()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_patch_outbound_detail()** (6 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **DetailForCalculate** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_schema.py`
- *... and 21 more nodes in this community*

## Relationships

- [Outbound Order Schema Module (65)](Outbound_Order_Schema_Module_65.md) (15 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (13 shared connections)
- [Outbound Order Service Module (123)](Outbound_Order_Service_Module_123.md) (12 shared connections)
- [Warehouse Outbound Operations (117)](Warehouse_Outbound_Operations_117.md) (10 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (8 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (6 shared connections)
- [Frontend API & Data Services (13)](Frontend_API_&_Data_Services_13.md) (6 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (5 shared connections)
- [AMR Fleet & Robot Integration (130)](AMR_Fleet_&_Robot_Integration_130.md) (5 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (4 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (4 shared connections)

## Source Files

- `backend/legacy_wms_archive/outbound_order/outbound_order_model.py`
- `backend/legacy_wms_archive/outbound_order/outbound_order_schema.py`
- `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`

## Audit Trail

- EXTRACTED: 165 (64%)
- INFERRED: 92 (36%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*