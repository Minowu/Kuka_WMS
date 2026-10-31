# FleetTask

> God node · 49 connections · `backend/app/modules/production/production_models.py`

**Community:** [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md)

## Connections by Relation

### contains
- production_models.py `EXTRACTED`

### imports
- location_service.py `EXTRACTED`
- route_api.py `EXTRACTED`
- dispatch_core.py `EXTRACTED`
- seed_production_core.py `EXTRACTED`
- env.py `EXTRACTED`
- kuka_fleet_client.py `EXTRACTED`
- production_celery_task.py `EXTRACTED`
- test_dispatch_engine.py `EXTRACTED`
- dispatch/__init__.py `EXTRACTED`
- reset_clean_data.py `EXTRACTED`
- test_cart_selector_same_machine.py `EXTRACTED`
- dashboard_service.py `EXTRACTED`
- test_kuka_fleet_replay.py `EXTRACTED`
- webhook_handler.py `EXTRACTED`
- cart_selector.py `EXTRACTED`
- queue_service.py `EXTRACTED`
- production/__init__.py `EXTRACTED`

### inherits
- Base `EXTRACTED`

### rationale_for
- Low-level AMR mission dispatched to KUKA Fleet Manager (/amr/submitMission). `EXTRACTED`

### references
- .lock_cart_and_dispatch_fleet_task() `EXTRACTED`
- .fleet_move_empty_container() `EXTRACTED`
- .submit_fleet_task() `EXTRACTED`
- .complete_fleet_task() `EXTRACTED`
- .fleet_move_material() `EXTRACTED`
- .fleet_move_to_wash() `EXTRACTED`
- .fleet_move_empty_rack() `EXTRACTED`
- ._lock_cart_and_dispatch_fleet_task() `EXTRACTED`
- .complete_fleet_task() `EXTRACTED`
- .create_fleet_task() `EXTRACTED`

### uses
- [DispatchService](DispatchService.md) `INFERRED`
- KukaFleetClient `INFERRED`
- CartSelector `INFERRED`
- DispatchCore `INFERRED`
- get_pda_cnc_stations() `INFERRED`
- list_locations_for_map() `INFERRED`
- fail_and_release() `INFERRED`
- reset_clean_slate() `INFERRED`
- WebhookHandler `INFERRED`
- get_pda_washing_slots() `INFERRED`
- run_verification() `INFERRED`
- submit_fleet_task() `INFERRED`
- get_report_kpis() `INFERRED`
- run_kuka_fleet_replay_test() `INFERRED`
- reset_runtime_tables() `INFERRED`
- _get_recent_location_errors_batch() `INFERRED`
- sweep_fleet_tasks() `INFERRED`
- delete_location() `INFERRED`
- _get_recent_location_error() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*