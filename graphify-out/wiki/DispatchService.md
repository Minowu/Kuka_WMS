# DispatchService

> God node · 45 connections · `backend/app/modules/production/dispatch/__init__.py`

**Community:** [Production Dispatch & AMR Flow (19)](Production_Dispatch_&_AMR_Flow_19.md)

## Connections by Relation

### contains
- dispatch/__init__.py `EXTRACTED`

### imports
- dispatch_service.py `EXTRACTED`

### method
- .__init__() `EXTRACTED`
- ._lock_cart_and_dispatch_fleet_task() `EXTRACTED`
- .receive_task_status() `EXTRACTED`
- .complete_fleet_task() `EXTRACTED`
- .try_resolve_waiting_cart_queue() `EXTRACTED`
- .try_resolve_waiting_slot_queue() `EXTRACTED`
- .scan_all_transport_queues() `EXTRACTED`
- .create_fleet_task() `EXTRACTED`
- .get_stage_info_for_machine() `EXTRACTED`
- .find_fifo_available_cart() `EXTRACTED`
- .find_available_slot_to_wash() `EXTRACTED`
- .find_next_empty_buffer_slot() `EXTRACTED`
- .assign_locations_to_user() `EXTRACTED`
- .register_rack_at_raw_material() `EXTRACTED`
- .call_material_to_cnc() `EXTRACTED`
- .complete_machining_stage() `EXTRACTED`
- .complete_washing_and_return_empty_cart() `EXTRACTED`
- .submit_fleet_task() `EXTRACTED`
- .calculate_distance() `EXTRACTED`
- ._is_location_free() `EXTRACTED`
- *…and 11 more `method` connection(s) not listed (lowest-degree first to go)*

### rationale_for
- Facade orchestrating all modularized production dispatch sub-services. `EXTRACTED`

### uses
- [Location](Location.md) `INFERRED`
- [ItemStock](ItemStock.md) `INFERRED`
- [FleetTask](FleetTask.md) `INFERRED`
- TransportRequest `INFERRED`
- KukaFleetClient `INFERRED`
- UserLocation `INFERRED`
- CartSelector `INFERRED`
- DispatchCore `INFERRED`
- TaskStatus `INFERRED`
- QueueService `INFERRED`
- WebhookHandler `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*