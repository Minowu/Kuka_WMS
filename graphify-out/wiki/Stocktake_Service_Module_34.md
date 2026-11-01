# Stocktake Service Module (34)

> 42 nodes · cohesion 0.12

## Key Concepts

- **stocktake_service.py** (38 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **stocktake_schema.py** (17 connections) — `backend/legacy_wms_archive/stocktake/stocktake_schema.py`
- **Session** (15 connections)
- **create_stocktake()** (13 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **StocktakeItemStock** (9 connections) — `backend/legacy_wms_archive/stocktake/stocktake_model.py`
- **BaseModel** (9 connections)
- **get_stocktake_detail()** (9 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **decimal** (9 connections)
- **Stocktake** (8 connections) — `backend/legacy_wms_archive/stocktake/stocktake_model.py`
- **list_stocktake_items()** (8 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **record_stocktake_item_count()** (8 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **stocktake_item_to_response()** (8 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **get_stocktake_by_id()** (7 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **stocktake_to_response()** (7 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **StocktakeRecordCountRequest** (6 connections) — `backend/legacy_wms_archive/stocktake/stocktake_schema.py`
- **_apply_item_stock_metadata()** (6 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **_get_stocktake_item_row()** (6 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **_stocktake_item_query()** (6 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **StocktakeItemStockResponse** (5 connections) — `backend/legacy_wms_archive/stocktake/stocktake_schema.py`
- **confirm_quantity_for_stock()** (5 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **_ensure_item_and_location()** (5 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **get_stocktake_item_form_data()** (5 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **list_stocktakes()** (5 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **update_stocktake()** (5 connections) — `backend/legacy_wms_archive/stocktake/stocktake_service.py`
- **StocktakeCreate** (4 connections) — `backend/legacy_wms_archive/stocktake/stocktake_schema.py`
- *... and 17 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (13 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (8 shared connections)
- [Frontend API & Data Services (78)](Frontend_API_&_Data_Services_78.md) (7 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (5 shared connections)
- [Warehouse Outbound Operations (117)](Warehouse_Outbound_Operations_117.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (3 shared connections)
- [Stocktake Model Module (154)](Stocktake_Model_Module_154.md) (2 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (2 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (2 shared connections)
- [Warehouse Domain (49)](Warehouse_Domain_49.md) (2 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/stocktake/stocktake_model.py`
- `backend/legacy_wms_archive/stocktake/stocktake_schema.py`
- `backend/legacy_wms_archive/stocktake/stocktake_service.py`

## Audit Trail

- EXTRACTED: 122 (74%)
- INFERRED: 42 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*