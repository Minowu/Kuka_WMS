# History Schema Module (38)

> 38 nodes · cohesion 0.11

## Key Concepts

- **history_service.py** (24 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **history_schema.py** (20 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **get_transaction_history()** (12 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **Transaction** (11 connections) — `backend/legacy_wms_archive/transaction_history/history_model.py`
- **BaseModel** (11 connections)
- **sqlalchemy_exc** (10 connections)
- **Session** (8 connections)
- **HistoryResponse** (7 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **create_transaction()** (6 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **normalize_history_details()** (5 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **TransactionResponse** (5 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **_ensure_refs()** (5 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **list_histories()** (5 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **list_transactions()** (5 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **HistoryCreate** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **.coerce_details()** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **ItemStockLookupResponse** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **TransactionCreate** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **create_history()** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **_to_item_stock_lookup()** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **_to_transaction_history_item()** (4 connections) — `backend/legacy_wms_archive/transaction_history/history_service.py`
- **HistoryListResponse** (3 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **.set_lot_display()** (3 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **OrderBriefResponse** (3 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- **TransactionHistoryItemResponse** (3 connections) — `backend/legacy_wms_archive/transaction_history/history_schema.py`
- *... and 13 more nodes in this community*

## Relationships

- [Inbound Order Service Module (32)](Inbound_Order_Service_Module_32.md) (9 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (9 shared connections)
- [Frontend API & Data Services (97)](Frontend_API_&_Data_Services_97.md) (7 shared connections)
- [Outbound Order Service Module (27)](Outbound_Order_Service_Module_27.md) (6 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (4 shared connections)
- [Warehouse Domain (103)](Warehouse_Domain_103.md) (3 shared connections)
- [Stocktake Service Module (34)](Stocktake_Service_Module_34.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (2 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (2 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (1 shared connections)
- [Warehouse Location & Storage (71)](Warehouse_Location_&_Storage_71.md) (1 shared connections)
- [Authentication & User Access (41)](Authentication_&_User_Access_41.md) (1 shared connections)

## Source Files

- `backend/legacy_wms_archive/transaction_history/history_model.py`
- `backend/legacy_wms_archive/transaction_history/history_schema.py`
- `backend/legacy_wms_archive/transaction_history/history_service.py`

## Audit Trail

- EXTRACTED: 90 (71%)
- INFERRED: 36 (29%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*