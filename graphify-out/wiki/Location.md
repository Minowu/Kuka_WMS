# Location

> God node · 115 connections · `backend/app/modules/warehouse/location_map/location_model.py`

**Community:** [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md)

## Connections by Relation

### calls
- sync_locations_from_map() `EXTRACTED`
- upsert_location() `EXTRACTED`
- .test_cart_selector_excludes_same_machine_slots() `EXTRACTED`
- .test_raw_material_cart_exclusion_at_target_location() `EXTRACTED`

### contains
- location_model.py `EXTRACTED`

### imports
- location_service.py `EXTRACTED`
- qr_code_module.py `EXTRACTED`
- route_api.py `EXTRACTED`
- outbound_order_service.py `EXTRACTED`
- item_service.py `EXTRACTED`
- inbound_order_service.py `EXTRACTED`
- stocktake_service.py `EXTRACTED`
- dispatch_core.py `EXTRACTED`
- seed_production_core.py `EXTRACTED`
- env.py `EXTRACTED`
- item_model.py `EXTRACTED`
- kuka_fleet_client.py `EXTRACTED`
- production_celery_task.py `EXTRACTED`
- item_stock_service.py `EXTRACTED`
- test_dispatch_engine.py `EXTRACTED`
- dispatch/__init__.py `EXTRACTED`
- dashboard_snapshot_service.py `EXTRACTED`
- warehouse_service.py `EXTRACTED`
- history_service.py `EXTRACTED`
- reset_clean_data.py `EXTRACTED`
- *…and 10 more `imports` connection(s) not listed (lowest-degree first to go)*

### inherits
- Base `EXTRACTED`

### method
- .node_label() `EXTRACTED`
- .machine_code() `EXTRACTED`
- .zone_id() `EXTRACTED`

### rationale_for
- Warehouse location model for storing materials and products. `EXTRACTED`

### references
- .find_fifo_available_cart() `EXTRACTED`
- .find_available_slot_to_wash() `EXTRACTED`
- .find_next_empty_buffer_slot() `EXTRACTED`
- .get_stage_info_for_machine() `EXTRACTED`
- .calculate_distance() `EXTRACTED`
- .find_available_slot_to_wash() `EXTRACTED`
- .find_fifo_available_cart() `EXTRACTED`
- .find_next_empty_buffer_slot() `EXTRACTED`
- .get_stage_info_for_machine() `EXTRACTED`
- .calculate_distance() `EXTRACTED`

### uses
- [ItemStock](ItemStock.md) `INFERRED`
- [Item](Item.md) `INFERRED`
- [DispatchService](DispatchService.md) `INFERRED`
- KukaFleetClient `INFERRED`
- CartSelector `INFERRED`
- DispatchCore `INFERRED`
- get_pda_cnc_stations() `INFERRED`
- seed_production_core() `INFERRED`
- list_locations_for_map() `INFERRED`
- QueueService `INFERRED`
- reset_clean_slate() `INFERRED`
- ensure_location_has_no_stock() `INFERRED`
- WebhookHandler `INFERRED`
- get_pda_washing_slots() `INFERRED`
- create_stocktake() `INFERRED`
- run_verification() `INFERRED`
- submit_fleet_task() `INFERRED`
- get_report_kpis() `INFERRED`
- execute_outbound_task() `INFERRED`
- release_location() `INFERRED`
- *…and 45 more `uses` connection(s) not listed (lowest-degree first to go)*

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*