# Qr Code Module Module (33)

> 43 nodes · cohesion 0.13

## Key Concepts

- **qr_code_module.py** (83 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **json** (30 connections)
- **get_redis()** (28 connections) — `backend/app/core/cache.py`
- **cache_scan_keys()** (21 connections) — `backend/app/core/cache.py`
- **cache.py** (20 connections) — `backend/app/core/cache.py`
- **cache_set()** (16 connections) — `backend/app/core/cache.py`
- **cache_get()** (12 connections) — `backend/app/core/cache.py`
- **_qr_preview_payload()** (12 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **cache_delete_pattern()** (8 connections) — `backend/app/core/cache.py`
- **get_assigned_item_stock()** (8 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_get_cached_item_assign_for_qr()** (8 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_get_linked_packs_for_item_anchor()** (8 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **get_pending_by_packing_user()** (8 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **relocate_cached_item_stock()** (8 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_pack_qr_preview_payload_for_item_assign()** (7 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_get_cached_pending_for_qr()** (6 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_normalize_assigned_stock()** (6 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_prefixed_key()** (5 connections) — `backend/app/core/cache.py`
- **_apply_cached_preview_fields()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_check_pending_item_for_packing_user()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_check_qr_in_location()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_get_cached_assign_for_qr()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_reject_if_linked_pack_recache()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **_reject_if_pack_item_assign_conflict()** (5 connections) — `backend/legacy_wms_archive/inbound_order/qr_code_module.py`
- **app_modules_warehouse_transaction_history_history_model** (4 connections)
- *... and 18 more nodes in this community*

## Relationships

- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (50 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (20 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (9 shared connections)
- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (8 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (6 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (5 shared connections)
- [Main Module (109)](Main_Module_109.md) (5 shared connections)
- [Warehouse Domain (36)](Warehouse_Domain_36.md) (5 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (5 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Warehouse Location & Storage (63)](Warehouse_Location_&_Storage_63.md) (3 shared connections)

## Source Files

- `backend/app/core/cache.py`
- `backend/legacy_wms_archive/inbound_order/qr_code_module.py`

## Audit Trail

- EXTRACTED: 257 (99%)
- INFERRED: 2 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*