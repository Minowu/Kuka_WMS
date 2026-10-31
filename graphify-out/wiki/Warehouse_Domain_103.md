# Warehouse Domain (103)

> 13 nodes · cohesion 0.23

## Key Concepts

- **apply_lot_display_fields()** (24 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **lot_number_utils.py** (22 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **format_lot_value_for_display()** (11 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **resolve_lot_number_fields()** (9 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **format_lot_part_for_display()** (5 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **normalize_lot_number()** (4 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **.validate_lot_fields()** (3 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **.set_lot_display()** (3 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **.validate_lot_fields()** (3 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **model_validator** (3 connections)
- **Compact DDMMYY in DB → DD/MM/YY for API/UI. Does not parse or validate input.** (1 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **Format a single lot string, including compact ranges like 070826-080826.** (1 connections) — `backend/app/modules/warehouse/lot_number_utils.py`
- **Return (from, to, combined) formatted for API responses.** (1 connections) — `backend/app/modules/warehouse/lot_number_utils.py`

## Relationships

- [Inbound Order Schema Module (25)](Inbound_Order_Schema_Module_25.md) (9 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (8 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (7 shared connections)
- [Warehouse Domain (54)](Warehouse_Domain_54.md) (6 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (5 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (4 shared connections)
- [Warehouse Outbound Operations (117)](Warehouse_Outbound_Operations_117.md) (3 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (3 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (3 shared connections)
- [Outbound Order Schema Module (65)](Outbound_Order_Schema_Module_65.md) (2 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Warehouse Location & Storage (62)](Warehouse_Location_&_Storage_62.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- `backend/app/modules/warehouse/lot_number_utils.py`

## Audit Trail

- EXTRACTED: 72 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*