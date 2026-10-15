### TASK STATE
Transforming the KUKA_WMS repository from a legacy warehouse WMS into an AMR manufacturing line feeding and WIP transfer coordination system for CNC lines. Current milestone is Phase 0 (Architecture Alignment and Context Handoff). Immediate prior step completed: scanned current database schema, resolved 5 critical business logic grill questions (Euclidean calculation, automatic waiting queue for carts and wash slots, direct-to-first-CNC line feeding, autonomous drop-off), and updated DOCS/Context_chuyen_giao_du_an_tich_hop_AMR_chi_tiet.md (v1.2). Immediate next step queued: prune deprecated Masan FMCG modules and legacy warehouse operator UI, then implement the new manufacturing schema migration.

### CURRENT HEAD
Branch: dev (dedicated development branch, tracks origin/dev)
Commit: 70836ad docs: replace binary context docx with markdown spec and add handoff summary
Working tree: dirty (DOCS/Context_chuyen_giao_du_an_tich_hop_AMR_chi_tiet.md v1.2 and DOCS/handoff_summary.md pending commit)
Pushed: previous commit 70836ad pushed to origin/dev; local v1.2 updates uncommitted
Backend service: FastAPI with PostgreSQL 5433, Celery, Redis, SQLAlchemy, Alembic (docker-compose configured)
Deploy target: local Docker Compose dev environment
Other infra: remote connection isolated exclusively to https://github.com/Minowu/Kuka_WMS.git (all upstream remotes removed)

### DECISIONS LOCKED
**Product:** Scope is discrete manufacturing line dispatch, not warehouse WMS (do not weaken). Three lifecycles remain decoupled: transport request, cart production progress, and FM task state (do not weaken). Flow B auto-scans map, computes 2D Euclidean distance, and assigns nearest valid cart. Flow A delivers directly to the first CNC station of the model. Autonomous AMR drop-off confirmed (no manual worker confirmation on tablet).
**Queueing:** Background automated queueing enabled for waiting stations (when no cart is ready) and waiting wash slots (when wash area is full); system automatically dispatches as soon as prerequisite condition clears.
**Architecture:** Retain FastAPI, PostgreSQL, Celery worker queue, WebSocket manager, Auth RBAC, and admin pages. Purge Masan FMCG modules and legacy warehouse operator UI (inbound, outbound, sorting, stocktake).
**Database:** Keep location table 100% intact for factory stations and map coordinates. Repurpose item as Product Model and item_stock as Cart/WIP (add cart_code, last_completed_step_id, is_locked). Deprecate legacy warehouse order/stocktake tables. Add production_route, route_step, transport_request, transport_queue, fleet_task, production_record.
**Tooling:** Working branch locked to dev; main reserved for stable releases.

### ACTIVE GOTCHAS
- Cart eligibility requires three checks: previous CNC step confirmed complete, destination CNC is valid next step in model route, and cart is not locked by another task.
- Operator confirming production completion is NOT AMR task completion; FM task accept is NOT cart delivered; never conflate these three state lifecycles.
- Distance calculation uses 2D Euclidean distance on layout coordinates (map_x, map_y); do not invoke routing algorithms for cart selection.
- Database port in docker-compose.yml is mapped to 5433 to avoid host port 5432 conflict; connection configs must use 5433.
- Station codes in internal database must map to Fleet Manager node IDs; do not assume identical naming conventions.
- Frontend tablet UI relies on dedicated tablet scaling CSS (operatorTabletScale.css); do not replace with desktop responsive wrappers.

### OPEN QUESTIONS
- Fleet Manager API schema, auth, task creation payload, and polling vs webhook mechanism unconfirmed; vendor documentation required (resolve before Fleet Adapter implementation).
- Mapping between factory map coordinates/stations and physical AMR Fleet Manager map node IDs (resolve during Fleet Adapter integration).
- Definition of "no carts currently running" condition required before admin can edit active routes (resolve before Route Management API implementation).

### ARCHIVE POINTER
Full session log: none committed.
Reference docs:
- Business context specification: DOCS/Context_chuyen_giao_du_an_tich_hop_AMR_chi_tiet.md (v1.2)
- Context handoff skill guide: DOCS/summary_context_skill.md

### NEXT STEP
```
Resuming KUKA AMR integration project on branch dev.
Begin Phase 1: remove deprecated Masan modules and legacy warehouse operator pages, then create the new manufacturing database models and migration.
The attached handoff is authoritative; read it before acting.
```
