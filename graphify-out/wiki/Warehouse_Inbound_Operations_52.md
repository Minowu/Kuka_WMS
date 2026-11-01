# Warehouse Inbound Operations (52)

> 31 nodes · cohesion 0.18

## Key Concepts

- **format_lot_number_display()** (23 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **assign_or_get_item_stock()** (20 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **assign_stock_to_location()** (19 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **assign_for_packing_user()** (17 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **assign_packing_to_item()** (15 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_cache_qr_manual()** (14 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **Session** (13 connections)
- **AssignOrGetItemStockAction** (11 connections) — `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`
- **resolve_lot_number_input()** (10 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **_cavity_numbers_from_item()** (10 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_qr_type_needs_qc_packing()** (10 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_item_stock_preview_payload()** (8 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_normalize_qr_type()** (7 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_resolve_location()** (7 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_validate_staff_for_location_assign()** (7 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_existing_stock_preview_result()** (6 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **preview_qr_code()** (6 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_preview_result()** (6 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_stock_level_for_qr_type()** (6 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_apply_split_flag_to_cache_payload()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_location_stocks_result()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **get_cavity_numbers()** (4 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_location_scan_result()** (4 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_reject_pack_and_transit_for_location_assign()** (4 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_assigned_result()** (3 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- *... and 6 more nodes in this community*

## Relationships

- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (50 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (7 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (6 shared connections)
- [Frontend API & Data Services (13)](Frontend_API_&_Data_Services_13.md) (5 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (4 shared connections)
- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (3 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (3 shared connections)
- [Inbound Order Schema Module (25)](Inbound_Order_Schema_Module_25.md) (3 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (3 shared connections)
- [Outbound Order Service Module (123)](Outbound_Order_Service_Module_123.md) (1 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (1 shared connections)
- [Warehouse Outbound Operations (117)](Warehouse_Outbound_Operations_117.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/lot_number_utils.py`
- `backend/legacy_wms_archive/inbound_order/inbound_order_schema.py`
- `backend/legacy_wms_archive/inbound_order/qr_code_module.py`

## Audit Trail

- EXTRACTED: 146 (86%)
- INFERRED: 23 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*