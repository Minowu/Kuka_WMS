# Onboarding: kiến trúc backend sau Clean Architecture (mức C)

> Dành cho người mới. Đọc theo thứ tự mục **1 → 2 → 4**, rồi trả lời mục **Q&A**.

---

## 1) Bản đồ kiến trúc (đọc theo thứ tự này)

| Thứ tự | Tầng | Path chính | Việc của tầng |
|---|---|---|---|
| 0 | Entry | `backend/app/main.py` | Mount router `/api/v1` |
| 1 | Adapter API (Strangler) | `adapters/api/v1/*` | Re-export router từ `modules/` (điểm gắn ổn định) |
| 2 | Thin router | `modules/production/<feature>/api.py` | Auth, validate input, gọi factory, map lỗi HTTP |
| 3 | DI / wiring | `infrastructure/di/*_factory.py` | Ghép use case + adapters thật |
| 4 | Use case | `application/*/use_cases/**` | Orchestration nghiệp vụ |
| 5 | Ports | `application/*/ports/**` | Interface (ABC) — “cần gì”, chưa biết “làm thế nào” |
| 6 | Domain | `domain/**` | Entity / VO / rule thuần (vd `TransportRequest.create_call_cnc`) |
| 7 | Adapters | `infrastructure/external_services/**`, `.../repositories/**` | SQLAlchemy, CartSelector, Fleet, Socket |
| 8 | ORM | `infrastructure/.../production_orm.py` | Table definitions (`modules` chỉ re-export) |

### Thuật ngữ

- **Dependency Rule:** code tầng trong (domain / use case) **không** import FastAPI / SQLAlchemy. Tầng ngoài implement ports và “hướng vào trong”.
- **Strangler:** hệ thống cũ (`modules/`) vẫn làm thin API / facade; logic mới nằm ở `application` + `infrastructure`, thay dần không big-bang.
- **Deep port:** use case gọi nhiều port hẹp (lookup, mutator, dispatcher…) thay vì một executor bọc nguyên file cũ.
- **Thin router:** file API chỉ nhận HTTP → gọi use case / service → trả JSON; không chứa SQL nghiệp vụ.

### Feature folder trong `modules/production`

Mỗi nghiệp vụ gom vào một folder:

```
modules/production/
  pda/          api.py, service.py, schema.py
  dispatch/     api.py, service.py, schema.py, ops/, fleet client…
  fleet/        api.py
  rack/         api.py, service.py, schema.py, policy/query/…
  machine/      api.py, service.py, schema.py, service_pkg/
  station/      api.py, service.py, schema.py
  routes/       api.py, service.py, schema.py, service_pkg/, aggregator.py
  andon/        api.py, service.py, schema.py
  request/      api.py, service.py, schema.py
  user_locations/ api.py, service.py
```

File cũ kiểu `pda_api.py` (nếu còn) chỉ là **shim re-export** để import cũ không gãy.

---

## 2) Luồng 1 service chuẩn — `call_material`

Đây là mẫu sạch nhất để người mới học.

```
PDA / client
  POST /api/v1/production/dispatch/call-material
        │
        ▼
main.py
  → adapters/api/v1/production   (re-export)
  → modules/production/routes/aggregator.py (include sub-routers)
  → modules/production/dispatch/api.py
        │
        ├─ get_current_user / ensure_user_can_access_location
        ├─ get_call_material_use_case(db)   ← production_factory
        └─ use_case.execute(CallMaterialRequest(...))
                │
                ▼
        CallMaterialUseCase (application)
                │  gọi ports lần lượt:
                ├─ ILocationGuard          → vị trí đích còn trống?
                ├─ IStageResolver          → cần stage level nào?
                ├─ TransportRequest (domain) + ITransportRequestRepository.save
                ├─ ICartFinder             → có xe FIFO không?
                ├─ có xe → IFleetDispatcher.lock_cart_and_dispatch
                │  không → mark queued + ITransportQueue.enqueue_waiting_cart
                ├─ ICallMaterialUnitOfWork.commit
                └─ (nếu queue) IFloorNotifier.notify...
                │
                ▼
        Adapters (infrastructure/.../call_material_adapters.py)
                │  SQLAlchemy / CartSelector / QueueService / lock_cart / event_bus
                ▼
        DB + (async) Fleet submit qua Celery nếu đã tạo FleetTask
```

### Điểm cần nắm

| Lớp | Biết | Không biết |
|---|---|---|
| Thin router | HTTP, auth, DTO | SQLAlchemy query, Fleet HTTP |
| Use case | Thứ tự nghiệp vụ + ports | Class ORM / FastAPI |
| Adapter | ORM, CartSelector, Fleet | “Khi nào gọi” (do use case quyết) |
| Factory | Ghép port → adapter | Nghiệp vụ |

Các flow CNC khác (`complete_stage`, `register_rack`, `return_empty`) **cùng hình dạng**, khác bộ ports.

### Nhánh async (đọc sau khi nắm sync)

- Submit Fleet: Celery `submit_fleet_task` → `SubmitTaskUseCase` → `IFleetSubmitter`
- Webhook: Celery / HTTP → `HandleWebhookUseCase` → `WebhookHandler`
- Chi tiết protocol: `DOCS/fleet_webhook_protocol.md`

---

## 4) Checklist “đã hiểu 1 service”

Tự trả lời được 5 câu:

1. Request HTTP vào file nào trước? (`main` → adapter API → aggregator → thin router)
2. Ai tạo use case (DI)? (`infrastructure/di/production_factory.py`)
3. Use case phụ thuộc interface nào, không phụ thuộc class nào? (ports ABC; không phụ thuộc SQLAlchemy model)
4. Adapter nào chạm DB / Fleet?
5. Nhánh “có xe” vs “không có xe” xử lý ở đâu? (trong use case, sau `ICartFinder`)

### Lộ trình đọc 1–2 ngày

1. Nghiệp vụ: `TODO/04_BUSINESS_LOGIC_ANALYSIS.md`
2. Kiến trúc mục tiêu: `TODO/01_CLEAN_ARCHITECTURE_PLAN.md` §1–2 + `TODO/PROGRESS_CLEAN_ARCHITECTURE.md`
3. Entry: `main.py` → `adapters/api/v1/production` → `dispatch/api.py`
4. 1 use case E2E: `call_material` + ports + adapters + factory
5. Lặp: `complete_stage` → `register_rack` → `return_empty`
6. Async: `fleet_webhook_protocol.md` + Celery tasks
7. Test sống: `tests/unit/application/production/`

---

## Q&A: Vì sao cần `adapters/api` — sao không gọi thẳng Thin router?

**Câu hỏi:** `main.py` đã có thể `include_router` từ `modules/production/.../api.py`. Vậy `app/adapters/api/v1/*` để làm gì?

**Trả lời ngắn:** Adapter API là **lớp gắn ổn định (stable entry)** theo Strangler Fig — không phải chỗ chứa thêm business logic.

### Vai trò cụ thể

1. **Điểm import cố định cho Presentation layer**  
   `main.py` chỉ phụ thuộc `app.adapters.api.v1.*`. Khi bên trong đổi (`pda_api.py` → `pda/api.py`, tách package…), **chỉ sửa re-export trong adapters**, không sửa hàng loạt `main` / deploy entry.

2. **Ranh giới Clean Architecture**  
   Theo plan 5 tầng, Presentation/Adapters là vòng ngoài. Thin router trong `modules/` vẫn mang “mùi” modular monolith cũ. `adapters/api` đánh dấu rõ: *đây là cổng HTTP chính thức của hệ thống mới*.

3. **Chỗ mở rộng sau này không đụng modules**  
   Có thể thêm: versioning (`v2`), middleware/schema adapter, compose nhiều router, hoặc thay dần thin router bằng controller mới — vẫn giữ path `adapters/api/v1` cho `main.py`.

4. **Không phải tầng “thừa” nếu chỉ re-export**  
   Hiện tại nhiều file chỉ `from modules... import router` — đúng với giai đoạn Strangler. Mục tiêu không phải copy logic, mà **cố định mặt ngoài**, để `modules/` được gom folder / chuyển use case bên trong.

### Khi nào được bỏ / làm mỏng hơn?

Khi mọi router đã nằm gọn theo feature và team thống nhất một convention import, có thể để `adapters/api` siêu mỏng (1 file aggregate). **Vẫn nên giữ một điểm gắn** thay vì `main.py` import sâu vào từng `modules/.../api.py`, để tránh coupling entrypoint với cấu trúc nội bộ.

---

## Tham chiếu nhanh

| Chủ đề | File |
|---|---|
| Tiến độ CA mức C | `TODO/PROGRESS_CLEAN_ARCHITECTURE.md` |
| Plan 5 tầng | `TODO/01_CLEAN_ARCHITECTURE_PLAN.md` |
| Fleet webhook | `DOCS/fleet_webhook_protocol.md` |
| Call material use case | `application/production/use_cases/cnc_operations/call_material.py` |
| DI production | `infrastructure/di/production_factory.py` |
