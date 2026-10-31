# Warehouse Outbound Operations (117)

> 10 nodes · cohesion 0.24

## Key Concepts

- **parse_legacy_lot_number()** (11 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **_strategy_loading_stocks()** (9 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **lot_string_to_date()** (7 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **to_compact()** (3 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **_lot_as_date()** (3 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **re** (3 connections)
- **slash_to_compact()** (2 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **validate_ddmmyy()** (2 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **_lot_sort_key()** (2 connections) — `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`
- **date** (1 connections)

## Relationships

- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (10 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (4 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (3 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (1 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (1 shared connections)
- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/lot_number_utils.py`
- `backend/legacy_wms_archive/outbound_order/outbound_order_service.py`

## Audit Trail

- EXTRACTED: 30 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*