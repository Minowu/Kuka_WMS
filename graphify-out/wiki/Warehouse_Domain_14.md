# Warehouse Domain (14)

> 59 nodes · cohesion 0.08

## Key Concepts

- **item_service.py** (61 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **item_api.py** (31 connections) — `backend/app/modules/warehouse/item/item_api.py`
- **item_schema.py** (21 connections) — `backend/app/modules/warehouse/item/item_schema.py`
- **BaseModel** (11 connections)
- **analyze_items()** (11 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **Session** (11 connections)
- **get_item_detail()** (10 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **ItemResponse** (9 connections) — `backend/app/modules/warehouse/item/item_schema.py`
- **start_item_masan_import()** (9 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **DbSession** (8 connections)
- **_ensure_warehouse_exists()** (8 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **get_last_import_item_file()** (8 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **update_item()** (7 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **create_item()** (6 connections) — `backend/app/modules/warehouse/item/item_api.py`
- **update_item()** (6 connections) — `backend/app/modules/warehouse/item/item_api.py`
- **ItemCreate** (6 connections) — `backend/app/modules/warehouse/item/item_schema.py`
- **ItemUpdate** (6 connections) — `backend/app/modules/warehouse/item/item_schema.py`
- **create_item()** (6 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **delete_item()** (6 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **get_item_by_id()** (6 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **list_items()** (6 connections) — `backend/app/modules/warehouse/item/item_service.py`
- **import_items_masan()** (5 connections) — `backend/app/modules/warehouse/item/item_api.py`
- **get** (5 connections)
- **ItemAnalyzeResponse** (5 connections) — `backend/app/modules/warehouse/item/item_schema.py`
- **ItemDetailResponse** (5 connections) — `backend/app/modules/warehouse/item/item_schema.py`
- *... and 34 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (22 shared connections)
- [Warehouse Domain (36)](Warehouse_Domain_36.md) (21 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (6 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (4 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (4 shared connections)
- [Main Module (109)](Main_Module_109.md) (3 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (3 shared connections)
- [Production Routes & Operations (70)](Production_Routes_&_Operations_70.md) (2 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (2 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (2 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (1 shared connections)

## Source Files

- `backend/app/modules/warehouse/item/__init__.py`
- `backend/app/modules/warehouse/item/item_api.py`
- `backend/app/modules/warehouse/item/item_schema.py`
- `backend/app/modules/warehouse/item/item_service.py`

## Audit Trail

- EXTRACTED: 197 (91%)
- INFERRED: 20 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*