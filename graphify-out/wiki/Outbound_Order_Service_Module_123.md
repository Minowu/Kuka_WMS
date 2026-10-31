# Outbound Order Service Module (123)

> 9 nodes · cohesion 0.28

## Key Concepts

- **get_outbound_robot_tasks()** (11 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **_build_allocation_response()** (7 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **OutboundOrderAllocationResponse** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_schema.py`
- **OutboundRobotTaskResponse** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_schema.py`
- **_build_manual_allocation_task_from_group()** (5 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **.set_lot_display()** (3 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_schema.py`
- **_parse_task_path()** (3 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **model_validator** (1 connections)
- **_resolve_task_type()** (1 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`

## Relationships

- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (12 shared connections)
- [Outbound Order Schema Module (65)](Outbound_Order_Schema_Module_65.md) (4 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (1 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (1 shared connections)
- [AMR Fleet & Robot Integration (130)](AMR_Fleet_&_Robot_Integration_130.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/outbound_order/outbound_order_schema.py`
- `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`

## Audit Trail

- EXTRACTED: 20 (65%)
- INFERRED: 11 (35%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*