### TASK STATE
Transforming the KUKA_WMS repository from a legacy warehouse WMS into an AMR manufacturing line feeding and WIP transfer coordination system for CNC lines. Current milestone is Phase 0 (Architecture Alignment and Context Handoff). Immediate prior step completed: updated DOCS/Context_chuyen_giao_du_an_tich_hop_AMR_chi_tiet.md to lock in automatic map scanning and nearest-cart dispatch for Flow B. Immediate next step queued: prune deprecated Masan FMCG modules and legacy warehouse operator pages while preserving core backend infrastructure and admin pages.

### CURRENT HEAD
Branch: dev (dedicated development branch, tracks origin/dev)
Commit: e4fefb5 feat: sync warehouse maps, docs, configuration and add root .gitignore
Working tree: dirty (DOCS/Context_chuyen_giao_du_an_tich_hop_AMR_chi_tiet.md v1.1 and DOCS/handoff_summary.md pending commit)
Pushed: commit e4fefb5 pushed to origin/dev; local v1.1 documentation updates uncommitted
Backend service: FastAPI with PostgreSQL 5433, Celery, Redis, SQLAlchemy, Alembic (docker-compose configured)
Deploy target: local Docker Compose dev environment
Other infra: remote connection isolated exclusively to https://github.com/Minowu/Kuka_WMS.git (all upstream remotes removed)

### DECISIONS LOCKED
**Product:** System scope is discrete manufacturing line dispatch, not generic warehouse WMS (do not weaken). Three lifecycles must remain decoupled: transport request, cart production progress, and FM task state (do not weaken). For Flow B, operator selects Model only; system scans layout map and dispatches the nearest valid cart. No silent background queuing if no cart is eligible; notify the operator immediately (do not weaken).
**Architecture:** Retain FastAPI, PostgreSQL, Celery worker queue, WebSocket manager, and admin management pages. Purge Masan FMCG modules (app/modules/masan/) and legacy warehouse operator UI (inbound, outbound, sorting, stocktake).
**Tooling:** Primary development branch locked to dev; main reserved for stable releases.

### ACTIVE GOTCHAS
- Cart eligibility requires three checks: previous CNC step confirmed complete, destination CNC is valid next step in model route, and cart is not locked by another task.
- Operator confirming production completion is NOT AMR task completion; FM task accept is NOT cart delivered; never conflate these three state lifecycles.
- Windows terminal stdout default encoding cp1258 throws UnicodeEncodeError on Vietnamese docx text; use UTF-8 file output or Python UTF-8 encoding wrappers.
- PostgreSQL host port is mapped to 5433 in docker-compose.yml to avoid conflicts with local port 5432; connection configs must use 5433.
- Station codes in internal database must map to Fleet Manager node IDs; do not assume identical naming conventions.
- Frontend tablet UI relies on dedicated tablet scaling CSS (operatorTabletScale.css); do not replace with desktop responsive wrappers.

### OPEN QUESTIONS
- Fleet Manager API schema, auth, task creation payload, and polling vs webhook mechanism unconfirmed; vendor documentation required (resolve before Fleet Adapter implementation).
- Physical cart pickup and drop-off mechanism: autonomous AMR lifting vs manual operator docking assistance unconfirmed (resolve before tablet UI workflow completion).
- Handling when all wash slots are full at final CNC completion: hold at machine, reject, or buffer zone (resolve before Flow C implementation).
- Concrete criteria defining "no carts currently running" required before admin can edit active routes (resolve before Route Management API implementation).

### ARCHIVE POINTER
Full session log: none committed.
Reference docs:
- Business context specification: DOCS/Context_chuyen_giao_du_an_tich_hop_AMR_chi_tiet.md (v1.1)
- Context handoff skill guide: DOCS/summary_context_skill.md

### NEXT STEP
```
Resuming KUKA AMR integration project on branch dev.
Begin codebase cleanup: remove deprecated Masan modules and legacy warehouse operator pages while retaining admin pages and core backend.
The attached handoff is authoritative; read it before acting.
```
