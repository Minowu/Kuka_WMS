# Production Dispatch & AMR Flow (19)

> 52 nodes · cohesion 0.07

## Key Concepts

- **DispatchService** (45 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **KukaFleetClient** (31 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **._post_kuka()** (15 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **Any** (13 connections)
- **IcsError** (10 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **Session** (10 connections)
- **.fleet_move_empty_container()** (9 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.submit_fleet_task()** (9 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_container_out()** (8 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_move_material()** (8 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_move_to_wash()** (8 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_container_in()** (7 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_insert_rack()** (7 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_move_empty_rack()** (7 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.add_task()** (5 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **._do_fleet_call()** (5 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_cancel_task()** (5 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.fleet_remove_rack()** (5 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.create_fleet_task()** (4 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **.submit_fleet_task()** (3 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **_ics_configured()** (3 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.build_mission_payload()** (3 connections) — `backend/app/modules/production/dispatch/kuka_fleet_client.py`
- **.add_task()** (2 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **.fleet_cancel_task()** (2 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **.fleet_container_in()** (2 connections) — `backend/app/modules/production/dispatch/__init__.py`
- *... and 27 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (23 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (22 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (9 shared connections)
- [Production Dispatch & AMR Flow (116)](Production_Dispatch_&_AMR_Flow_116.md) (5 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (3 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)

## Source Files

- `backend/app/modules/production/dispatch/__init__.py`
- `backend/app/modules/production/dispatch/kuka_fleet_client.py`

## Audit Trail

- EXTRACTED: 130 (80%)
- INFERRED: 32 (20%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*