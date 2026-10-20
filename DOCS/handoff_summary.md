### TASK STATE
Completed Phase 1–4 of the KUKA AMR CNC line feeding & WIP transfer coordination system:
- Pruned all 17 legacy FMCG warehouse tables (`inbound_order*`, `outbound_order*`, `stocktake*`, `zone`, `unit`, `item_unit`, `qr_code`, `robot_task`, `transaction`, `history`, `inventory_daily_snapshot`, `item_import_staging`, `item_stock_relation`) and cleaned `item_stock` down to 14 WIP Cart columns.
- Normalized the schema to 3NF (22 core tables + `alembic_version`, head revision `e7f8a9b0c1d2`): added `machine`, `route_step_machine`, and `task_status`; removed `zone`.
- Implemented and verified 100% of the Dispatch Engine (`DispatchService` in `backend/app/modules/production/dispatch_service.py`) and Always-Scan Celery Beat task (`production.scan_transport_queue` every 5s).

### CURRENT HEAD
Branch: `dev` (tracks `origin/dev`)
Database: PostgreSQL on `localhost:5433/kuka` (and `WMS_db`), upgraded to Alembic `e7f8a9b0c1d2` (`head`) and seeded via `backend/scripts/seed_production_core.py`.

### DECISIONS LOCKED
- **Unrestricted User Location Assignment**: `assign_locations_to_user` assigns any number of stations to a user without artificial limits.
- **Raw Material QR Registration (`RAW_MATERIAL` 1..7)**: Operator selects location + Model + scans QR (`cart_code`) -> calls `fleet_insert_rack` (`/ics/shelf/insert`), creates/reactivates `ItemStock` (`current_stage_level = 0`, `status = 'available'`, `is_active = True`), and triggers queue resolution.
- **CNC Call Material (`call_material_to_cnc`)**:
  - Automatically infers `required_stage_level` from the normalized 3NF `ProductionRoute` -> `RouteStep` -> `RouteStepMachine` (`get_stage_info_for_machine`) when omitted.
  - Level 0 uses **FIFO** (`created_at ASC`); Level > 0 uses **2D Euclidean distance** (`map_x`, `map_y`) + FIFO tie-breaker with `FOR UPDATE OF item_stock SKIP LOCKED`.
  - Automatically falls back from `POS1` to `POS2` of the same CNC machine if `POS1` is occupied/reserved.
  - Enqueues into `TransportQueue` (`WAITING_CART`) if no cart is currently ready.
- **CNC Complete Stage (`complete_machining_stage`)**:
  - **Intermediate CNC Step (`is_final_cnc_step = False`)**: **Pull + Always-Scan** — increments `cart.current_stage_level`, unlocks cart (`status = 'available'`), and immediately checks `WAITING_CART`. Does NOT blindly push to the next machine if no downstream machine has called.
  - **Final CNC Step (`is_final_cnc_step = True`)**: Automatically dispatches `MOVE_TO_WASH` to an available `WASHING_SLOT` (`WASH-01..04`) or enqueues in `WAITING_SLOT`.
- **Empty Cart Buffer (`EMPTY_CART_BUFFER` 1..4) Round-Robin & Auto-Delete on Dropoff**:
  - Sequential Round-Robin allocation (`EMPTY-01 -> EMPTY-02 -> EMPTY-03 -> EMPTY-04 -> EMPTY-01`) via `find_next_empty_buffer_slot`.
  - Opposite of Raw Material insert: when KUKA Fleet webhook (`/receive-status`, `status = '8'` or `'9'`) reports dropoff at `EMPTY_CART_BUFFER`, `complete_fleet_task` immediately calls `fleet_remove_rack` (`/ics/shelf/remove`) and sets `cart.location_id = None, cart.destination_location_id = None, cart.quantity = 0, cart.current_stage_level = 0, cart.status = 'empty', cart.is_active = False, cart.is_locked = False`.
- **Always-Scan Queue Worker**: Celery Beat runs `production.scan_transport_queue` every 5 seconds alongside reactive event triggers.

### REFERENCE DOCS
- Master Database & Flow Blueprint: `DOCS/kuka_core_database_blueprint.md`
- Active Core Modules & Functions Reference: `DOCS/01_core_modules_and_functions_reference.md`
- End-to-End Verification Script: `backend/scripts/test_dispatch_engine.py`
