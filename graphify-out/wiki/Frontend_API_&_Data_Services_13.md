# Frontend API & Data Services (13)

> 60 nodes · cohesion 0.08

## Key Concepts

- **unit_service.py** (24 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **unit_api.py** (23 connections) — `backend/legacy_wms_archive/unit/unit_api.py`
- **Unit** (17 connections) — `backend/legacy_wms_archive/unit/unit_model.py`
- **unit_schema.py** (16 connections) — `backend/legacy_wms_archive/unit/unit_schema.py`
- **Session** (15 connections)
- **DbSession** (12 connections)
- **BaseModel** (12 connections)
- **ItemUnit** (11 connections) — `backend/legacy_wms_archive/unit/unit_model.py`
- **create_item_unit()** (8 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **update_item_unit()** (8 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **item_unit_to_response()** (7 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **UnitResponse** (6 connections) — `backend/legacy_wms_archive/unit/unit_schema.py`
- **get_item_unit_by_id()** (6 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **get_item_unit_by_item()** (6 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **create_item_unit()** (5 connections) — `backend/legacy_wms_archive/unit/unit_api.py`
- **create_unit()** (5 connections) — `backend/legacy_wms_archive/unit/unit_api.py`
- **get** (5 connections)
- **update_item_unit()** (5 connections) — `backend/legacy_wms_archive/unit/unit_api.py`
- **update_unit()** (5 connections) — `backend/legacy_wms_archive/unit/unit_api.py`
- **unit_model.py** (5 connections) — `backend/legacy_wms_archive/unit/unit_model.py`
- **convert_quantity()** (5 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **_ensure_item_exists()** (5 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **_ensure_item_unit_unique()** (5 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **_ensure_unit_exists()** (5 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- **get_unit_by_id()** (5 connections) — `backend/legacy_wms_archive/unit/unit_service.py`
- *... and 35 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (8 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (6 shared connections)
- [Warehouse Inbound Operations (52)](Warehouse_Inbound_Operations_52.md) (5 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (4 shared connections)
- [Dependencies Module (92)](Dependencies_Module_92.md) (3 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (3 shared connections)
- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (2 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (2 shared connections)
- [Main Module (109)](Main_Module_109.md) (1 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (1 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)
- [History Schema Module (38)](History_Schema_Module_38.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/unit/unit_api.py`
- `backend/legacy_wms_archive/unit/unit_model.py`
- `backend/legacy_wms_archive/unit/unit_schema.py`
- `backend/legacy_wms_archive/unit/unit_service.py`

## Audit Trail

- EXTRACTED: 138 (74%)
- INFERRED: 49 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*