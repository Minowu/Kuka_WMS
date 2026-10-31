# Item

> God node · 59 connections · `backend/app/modules/warehouse/item/item_model.py`

**Community:** [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md)

## Connections by Relation

### calls
- seed_production_core() `EXTRACTED`
- run_kuka_fleet_replay_test() `EXTRACTED`
- create_item() `EXTRACTED`

### contains
- item_model.py `EXTRACTED`

### imports
- qr_code_module.py `EXTRACTED`
- route_api.py `EXTRACTED`
- outbound_order_service.py `EXTRACTED`
- item_service.py `EXTRACTED`
- inbound_order_service.py `EXTRACTED`
- stocktake_service.py `EXTRACTED`
- dispatch_core.py `EXTRACTED`
- seed_production_core.py `EXTRACTED`
- env.py `EXTRACTED`
- dashboard_stock_aging_service.py `EXTRACTED`
- route_service.py `EXTRACTED`
- item_stock_service.py `EXTRACTED`
- test_dispatch_engine.py `EXTRACTED`
- dashboard_snapshot_service.py `EXTRACTED`
- warehouse_service.py `EXTRACTED`
- unit_service.py `EXTRACTED`
- reset_clean_data.py `EXTRACTED`
- test_cart_selector_same_machine.py `EXTRACTED`
- test_kuka_fleet_replay.py `EXTRACTED`
- dashboard_top_products_service.py `EXTRACTED`
- *…and 1 more `imports` connection(s) not listed (lowest-degree first to go)*

### inherits
- Base `EXTRACTED`

### method
- .unit_id() `EXTRACTED`

### rationale_for
- Item master data - represents product models / workpieces in CNC production. `EXTRACTED`

### uses
- [Location](Location.md) `INFERRED`
- [ItemStock](ItemStock.md) `INFERRED`
- DispatchCore `INFERRED`
- reset_clean_slate() `INFERRED`
- _create_stock_and_allocation() `INFERRED`
- get_report_stock_aging_overview() `INFERRED`
- run_verification() `INFERRED`
- get_report_stock_aging_bucket() `INFERRED`
- create_route() `INFERRED`
- update_route() `INFERRED`
- compute_live_total_inventory_value() `INFERRED`
- analyze_items() `INFERRED`
- TestCartSelectorSameMachine `INFERRED`
- _storage_stock_filters() `INFERRED`
- compute_live_total_quantity() `INFERRED`
- _top_stock() `INFERRED`
- _to_row() `INFERRED`
- delete_warehouse() `INFERRED`
- update_item() `INFERRED`
- get_pda_models() `INFERRED`
- *…and 11 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*