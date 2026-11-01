# Warehouse Domain (54)

> 30 nodes · cohesion 0.19

## Key Concepts

- **item_stock_service.py** (27 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **item_stock_api.py** (22 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **item_stock_schema.py** (15 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **ItemStockResponse** (10 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **get_stock_split()** (10 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **Session** (8 connections)
- **ItemStockCreate** (7 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **ItemStockUpdate** (7 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **get_item_stock_by_id()** (7 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **list_item_stocks()** (7 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **update_item_stock()** (7 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **create_item_stock()** (6 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **DbSession** (6 connections)
- **update_item_stock()** (6 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **create_item_stock()** (6 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **_ensure_item_and_location()** (6 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **_stock_query()** (6 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- **get_item_stock()** (5 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **ItemStockListResponse** (5 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **ItemStockSplitListResponse** (5 connections) — `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- **BaseModel** (5 connections)
- **delete_item_stock()** (4 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **get_stock_split()** (4 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **list_item_stocks()** (4 connections) — `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- **delete_item_stock()** (4 connections) — `backend/app/modules/warehouse/item_stock/item_stock_service.py`
- *... and 5 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (18 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (6 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (3 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (3 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (3 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (3 shared connections)
- [Main Module (109)](Main_Module_109.md) (2 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (1 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (1 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/item_stock/__init__.py`
- `backend/app/modules/warehouse/item_stock/item_stock_api.py`
- `backend/app/modules/warehouse/item_stock/item_stock_schema.py`
- `backend/app/modules/warehouse/item_stock/item_stock_service.py`

## Audit Trail

- EXTRACTED: 107 (86%)
- INFERRED: 17 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*