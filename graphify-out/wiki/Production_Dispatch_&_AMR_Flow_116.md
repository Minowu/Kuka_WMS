# Production Dispatch & AMR Flow (116)

> 10 nodes · cohesion 0.24

## Key Concepts

- **WebhookHandler** (13 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **.complete_fleet_task()** (9 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **.receive_task_status()** (9 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **.complete_fleet_task()** (4 connections) — `backend/app/modules/production/dispatch/__init__.py`
- **Any** (2 connections)
- **Session** (2 connections)
- **.__init__()** (2 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **Official completion handler when KUKA Fleet reports COMPLETED.** (1 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **Handles incoming KUKA Fleet callbacks (/api/v1/receive-status) and FSM…** (1 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`
- **Process incoming callback webhook from KUKA Fleet Manager (/api/v1/receive-…** (1 connections) — `backend/app/modules/production/dispatch/webhook_handler.py`

## Relationships

- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (6 shared connections)
- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (5 shared connections)
- [Production Dispatch & AMR Flow (19)](Production_Dispatch_&_AMR_Flow_19.md) (5 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (1 shared connections)
- [Production Dispatch & AMR Flow (42)](Production_Dispatch_&_AMR_Flow_42.md) (1 shared connections)

## Source Files

- `backend/app/modules/production/dispatch/__init__.py`
- `backend/app/modules/production/dispatch/webhook_handler.py`

## Audit Trail

- EXTRACTED: 24 (73%)
- INFERRED: 9 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*