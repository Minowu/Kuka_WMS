# Production Routes & Operations (70)

> 25 nodes · cohesion 0.21

## Key Concepts

- **route_service.py** (29 connections) — `backend/app/modules/production/route_service.py`
- **ProductionRoute** (26 connections) — `backend/app/modules/production/production_models.py`
- **RouteStep** (23 connections) — `backend/app/modules/production/production_models.py`
- **create_route()** (11 connections) — `backend/app/modules/production/route_service.py`
- **get_route_detail()** (11 connections) — `backend/app/modules/production/route_service.py`
- **update_route()** (11 connections) — `backend/app/modules/production/route_service.py`
- **ProductionRouteDetailResponse** (9 connections) — `backend/app/modules/production/route_schema.py`
- **list_routes()** (8 connections) — `backend/app/modules/production/route_service.py`
- **Session** (8 connections)
- **_sync_step_machines()** (8 connections) — `backend/app/modules/production/route_service.py`
- **_to_route_response()** (8 connections) — `backend/app/modules/production/route_service.py`
- **ProductionRouteResponse** (7 connections) — `backend/app/modules/production/route_schema.py`
- **ProductionRouteUpdate** (7 connections) — `backend/app/modules/production/route_schema.py`
- **activate_route()** (7 connections) — `backend/app/modules/production/route_service.py`
- **update_production_route()** (6 connections) — `backend/app/modules/production/route_api.py`
- **delete_route()** (5 connections) — `backend/app/modules/production/route_service.py`
- **ItemSummary** (4 connections) — `backend/app/modules/production/route_schema.py`
- **RouteStepResponse** (4 connections) — `backend/app/modules/production/route_schema.py`
- **_get_or_create_machine()** (4 connections) — `backend/app/modules/production/route_service.py`
- **put** (2 connections)
- **Production route definition per Item (Model).** (1 connections) — `backend/app/modules/production/production_models.py`
- **A processing stage within a production route (3NF: normalized step).** (1 connections) — `backend/app/modules/production/production_models.py`
- **.allowed_machines()** (1 connections) — `backend/app/modules/production/production_models.py`
- **Service layer for managing Production Routes and Route Steps (3NF).** (1 connections) — `backend/app/modules/production/route_service.py`
- **Populate normalized RouteStepMachine join rows for a RouteStep.** (1 connections) — `backend/app/modules/production/route_service.py`

## Relationships

- [Production Routes & Operations (8)](Production_Routes_&_Operations_8.md) (30 shared connections)
- [Alembic Database Migrations (9)](Alembic_Database_Migrations_9.md) (27 shared connections)
- [Production Dispatch & AMR Flow (10)](Production_Dispatch_&_AMR_Flow_10.md) (11 shared connections)
- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (4 shared connections)
- [Warehouse Domain (14)](Warehouse_Domain_14.md) (2 shared connections)
- [Production Dispatch & AMR Flow (16)](Production_Dispatch_&_AMR_Flow_16.md) (2 shared connections)
- [Alembic Database Migrations (0)](Alembic_Database_Migrations_0.md) (1 shared connections)

## Source Files

- `backend/app/modules/production/production_models.py`
- `backend/app/modules/production/route_api.py`
- `backend/app/modules/production/route_schema.py`
- `backend/app/modules/production/route_service.py`

## Audit Trail

- EXTRACTED: 105 (75%)
- INFERRED: 35 (25%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*