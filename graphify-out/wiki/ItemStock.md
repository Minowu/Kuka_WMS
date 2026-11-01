# ItemStock

> God node · 110 connections · `backend/app/modules/warehouse/item_stock/item_stock_model.py`

**Community:** [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md)

## Connections by Relation

### calls
- assign_stock_to_location() `EXTRACTED`
- seed_production_core() `EXTRACTED`
- _create_stock_and_allocation() `EXTRACTED`
- .register_rack_at_raw_material() `EXTRACTED`
- _clear_pending_cache_for_qr() `EXTRACTED`
- create_item_stock() `EXTRACTED`
- .test_cart_selector_excludes_same_machine_slots() `EXTRACTED`
- .test_raw_material_cart_exclusion_at_target_location() `EXTRACTED`

### contains
- item_stock_model.py `EXTRACTED`

### imports
- location_service.py `EXTRACTED`
- qr_code_module.py `EXTRACTED`
- route_api.py `EXTRACTED`
- outbound_order_service.py `EXTRACTED`
- item_service.py `EXTRACTED`
- inbound_order_service.py `EXTRACTED`
- location_model.py `EXTRACTED`
- stocktake_service.py `EXTRACTED`
- dispatch_core.py `EXTRACTED`
- seed_production_core.py `EXTRACTED`
- env.py `EXTRACTED`
- item_model.py `EXTRACTED`
- dashboard_stock_aging_service.py `EXTRACTED`
- route_service.py `EXTRACTED`
- item_stock_service.py `EXTRACTED`
- test_dispatch_engine.py `EXTRACTED`
- dispatch/__init__.py `EXTRACTED`
- dashboard_snapshot_service.py `EXTRACTED`
- history_service.py `EXTRACTED`
- reset_clean_data.py `EXTRACTED`
- *…and 8 more `imports` connection(s) not listed (lowest-degree first to go)*

### inherits
- Base `EXTRACTED`

### rationale_for
- Current item stock rows stored in warehouse locations (WIP Containers / Racks). `EXTRACTED`

### references
- .lock_cart_and_dispatch_fleet_task() `EXTRACTED`
- .find_fifo_available_cart() `EXTRACTED`
- ._lock_cart_and_dispatch_fleet_task() `EXTRACTED`

### uses
- [Location](Location.md) `INFERRED`
- [Item](Item.md) `INFERRED`
- [DispatchService](DispatchService.md) `INFERRED`
- CartSelector `INFERRED`
- DispatchCore `INFERRED`
- get_pda_cnc_stations() `INFERRED`
- QueueService `INFERRED`
- reset_clean_slate() `INFERRED`
- ensure_location_has_no_stock() `INFERRED`
- execute_inbound_task() `INFERRED`
- greedy_allocate_stocks_to_lines() `INFERRED`
- WebhookHandler `INFERRED`
- get_pda_washing_slots() `INFERRED`
- get_report_stock_aging_overview() `INFERRED`
- create_stocktake() `INFERRED`
- run_verification() `INFERRED`
- get_report_kpis() `INFERRED`
- get_report_stock_aging_bucket() `INFERRED`
- get_transaction_history() `INFERRED`
- create_route() `INFERRED`
- *…and 48 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*