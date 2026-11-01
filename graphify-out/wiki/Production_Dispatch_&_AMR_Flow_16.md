# Production Dispatch & AMR Flow (16)

> 57 nodes · cohesion 0.06

## Key Concepts

- **CartSelector** (26 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **DispatchCore** (23 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **publish_event()** (17 connections) — `backend/app/socket/event_bus.py`
- **QueueService** (15 connections) — `backend/app/modules/production/dispatch/queue_service.py`
- **.complete_machining_stage()** (14 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **.lock_cart_and_dispatch_fleet_task()** (13 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **Session** (13 connections)
- **.call_material_to_cnc()** (12 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **.complete_washing_and_return_empty_cart()** (11 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **.register_rack_at_raw_material()** (10 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **.try_resolve_waiting_cart_queue()** (9 connections) — `backend/app/modules/production/dispatch/queue_service.py`
- **.find_available_slot_to_wash()** (8 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **.find_next_empty_buffer_slot()** (8 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **.is_location_free()** (8 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **.try_resolve_waiting_slot_queue()** (8 connections) — `backend/app/modules/production/dispatch/queue_service.py`
- **.get_stage_info_for_machine()** (7 connections) — `backend/app/modules/production/dispatch/cart_selector.py`
- **Session** (6 connections)
- **.__init__()** (6 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **Session** (5 connections)
- **.assign_locations_to_user()** (5 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **.receive_task_status()** (5 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **.__init__()** (4 connections) — `backend/app/modules/production/dispatch/dispatch_core.py`
- **.assign_locations_to_user()** (4 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **.find_available_slot_to_wash()** (4 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **.find_fifo_available_cart()** (4 connections) — `backend/app/modules/production/dispatch/__init__.py`
- *... and 32 more nodes in this community*

## Relationships

- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (34 shared connections)
- [Production Dispatch & AMR Flow (19)](Production_Dispatch_&_AMR_Flow_19.md) (23 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (14 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (12 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (11 shared connections)
- [Production Dispatch & AMR Flow (116)](Production_Dispatch_&_AMR_Flow_116.md) (5 shared connections)
- [Production Routes & Operations (70)](Production_Routes_&_Operations_70.md) (2 shared connections)
- [Qr Code Module Module (33)](Qr_Code_Module_Module_33.md) (2 shared connections)

## Source Files

- `backend/app/modules/production/dispatch/__init__.py`
- `backend/app/modules/production/dispatch/cart_selector.py`
- `backend/app/modules/production/dispatch/dispatch_core.py`
- `backend/app/modules/production/dispatch/queue_service.py`
- `backend/app/socket/event_bus.py`
- `backend/tests/test_cart_selector_same_machine.py`

## Audit Trail

- EXTRACTED: 153 (74%)
- INFERRED: 53 (26%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*