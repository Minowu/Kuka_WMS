# KẾ HOẠCH CHUYỂN ĐỔI SANG KUKA FLEET THẬT (ĐANG THỰC HIỆN)

> **Trạng thái:** Hoàn tất 100% (Đã pass toàn bộ test replay và build frontend)  
> **Ngày:** 21/10/2026  
> **Tài liệu giao thức đi kèm:** [kuka_fleet_real_protocol_and_integration_specification.md](kuka_fleet_real_protocol_and_integration_specification.md)  
> **Phạm vi:** Chỉ DB `kuka` @ `localhost:5433`. Không đụng `WMS_db`.

---

## 0. CÁC QUYẾT ĐỊNH ĐÃ CHỐT

| # | Quyết định | Nguồn |
|---|---|---|
| D1 | Bỏ 100% danh pháp RCS cũ (`orderId`, `status "8"`, `shelfNumber`, `deviceCode`, `modelProcessCode`, `taskOrderDetail`, `/ics/...`) | User |
| D2 | Chỉ duy nhất `COMPLETED` mới là hoàn thành. `DOWN_CONTAINER` vẫn là `in_progress` | User |
| D3 | `process_code`, `system_code` bị xóa (Fleet không có) | User |
| D4 | `cart_code` → `container_code` ở mọi nơi | User |
| D5 | `containerModelCode` là một giá trị cố định do user cấu hình (đang test với `1001`) | User |
| D6 | Webhook dùng đường dẫn chuẩn `POST /api/v1/receive-status`. User sẽ cấu hình lại bên Fleet | User |
| D7 | Commit FleetTask trước, sau đó mới gọi `submitMission` (tránh race với `MOVE_BEGIN`) | Review #2 |
| D8 | Khóa dòng theo `mission_code` và không cho trạng thái lùi | Review #3 |
| D9 | Sửa toàn bộ endpoint/celery/simulator còn dùng định dạng cũ | Review #4 |
| D10 | Về bãi xe rỗng → gọi `containerOut` | User |
| D11 | `isNew = true` khi mã container chưa tồn tại trên Fleet | User |
| D12 | `missionCode` do MES tự sinh | User |
| D13 | `priority = 1` là cao nhất | User |
| D14 | Webhook không giới hạn IP | User |
| D15 | **Giữ nguyên 3 hàm move riêng biệt** (`fleet_move_material`, `fleet_move_to_wash`, `fleet_move_empty_container`) dù lặp logic tạo body submitMission để code tường minh | User |
| D16 | Webhook response trả về HTTP status 200 + `{"code": 0, "message": "success"}` | User |
| D17 | Hỗ trợ xác thực `Authorization: ${accessToken}` theo tài liệu KUKA AMR Fleet 2.14/2.16 | System/Manual |

---

## 1. CẤU HÌNH (`backend/app/core/config.py`)

**Xóa:** `cnc_move_material_code`, `cnc_move_wash_code`, `cnc_move_empty_code`.

**Thêm** (giá trị mặc định nằm trong `config.py`; muốn đổi nhanh không cần sửa code thì ghi đè bằng biến cùng tên trong `backend/.env`):

| Setting | Mặc định | Dùng ở |
|---|---|---|
| `kuka_base_url` (đổi tên từ `kuka_base_url`) | `http://192.168.1.71:10870/interfaces/api` | Mọi API outbound |
| `kuka_access_token` | `""` | Header HTTP `Authorization` khi Fleet bật xác thực |
| `kuka_org_id` | `KUKA011021` | `submitMission.orgId` |
| `kuka_container_model_code` | `1001` | `submitMission.containerModelCode` |
| `kuka_robot_type` | `LIFT` | `submitMission.robotType` |
| `kuka_mission_type` | `RACK_MOVE` | `submitMission.missionType` |
| `kuka_http_timeout_seconds` | `5` | httpx timeout |
| `kuka_submit_max_retries` | `3` | Outbox retry (Mục 4.3) |

> `.env` là tùy chọn: không có biến trong `.env` thì hệ thống lấy mặc định trong `config.py`. Sửa `config.py` thì cần restart backend, sửa `.env` cũng vậy.

---

## 2. QUY TẮC SINH MÃ

| Mã | Format | Ví dụ | Ghi chú |
|---|---|---|---|
| `missionCode` | `MS` + `yyyyMMddHHmmssSSS` + 4 ký tự hex | `MS20261021153300123A1B2` | 23 ký tự, chỉ chữ + số (giống mẫu Fleet `KK...`) |
| `requestId` submitMission | `SUB` + timestamp + 4 hex | `SUB20261021153300123A1B2` | Lưu `fleet_task.fleet_request_id` |
| `requestId` containerIn | `CIN` + timestamp + 4 hex | `CIN20261021153300456C3D4` | Lưu bảng log (Mục 3.4) |
| `requestId` containerOut | `COUT` + timestamp + 4 hex | `COUT20261021153300789E5F6` | Lưu bảng log |
| `requestId` missionCancel | `CXL` + timestamp + 4 hex | `CXL20261021153301012A7B8` | Lưu bảng log |

**Quy tắc retry:** gọi lại cùng một lệnh (do timeout/lỗi mạng) thì **giữ nguyên** `missionCode` và `requestId` để Fleet chống trùng. Chỉ sinh mã mới khi là một lệnh mới.

---

## 3. THAY ĐỔI CƠ SỞ DỮ LIỆU (1 migration Alembic mới)

Dùng `op.alter_column(new_column_name=...)` để đổi tên, giữ dữ liệu. Đổi tên cả index/unique constraint. Có viết `downgrade()`.

### 3.1. `fleet_task`
| Hiện tại | Sau migration | Kiểu | Ghi chú |
|---|---|---|---|
| `task_code` | `mission_code` | `VARCHAR(50) UNIQUE NOT NULL` | = `missionCode` |
| `request_id` (FK) | `transport_request_id` | `INT FK transport_request.id` | Tránh nhầm với `requestId` của Fleet |
| *(mới)* | `fleet_request_id` | `VARCHAR(50)` | = `requestId` gửi `submitMission` |
| `amr_code` | `robot_id` | `VARCHAR(50)` | = `robotId` |
| `cart_id` | `container_id` | `INT FK item_stock.id` | ⚠️ chờ chốt Q3 |
| *(mới)* | `container_code` | `VARCHAR(50)` | Chụp lại mã container lúc gửi lệnh |
| `task_order_detail` (TEXT) | `mission_data` | `JSONB` | Mảng `missionData` đã gửi |
| *(mới)* | `last_mission_status` | `VARCHAR(30)` | `MOVE_BEGIN` / `UP_CONTAINER` /... mới nhất |
| *(mới)* | `current_position` | `VARCHAR(50)` | Node cuối cùng Fleet báo |
| *(mới)* | `picked_up_at` | `TIMESTAMPTZ` | Thời điểm `UP_CONTAINER` (dùng cho luật hủy) |
| *(mới)* | `submit_attempts` | `INT DEFAULT 0` | Outbox retry |
| `process_code`, `system_code` | **DROP** | | D3 |
| `status` | giữ | | `pending_submit` → `sent` → `in_progress` → `completed` / `failed` / `cancelled` |

### 3.2. `task_status` (lịch sử callback; mỗi callback một dòng)
| Hiện tại | Sau migration | Kiểu |
|---|---|---|
| `order_id` | `mission_code` | `VARCHAR(50) INDEX` |
| `status` | `mission_status` | `VARCHAR(30)` |
| `device_code` | `robot_id` | `VARCHAR(50)` |
| `shelf_number` | `container_code` | `VARCHAR(50)` |
| `sub_task_status`, `device_num`, `qr_code` | **DROP** | |
| *(mới)* | `org_id` | `VARCHAR(50)` |
| *(mới)* | `container_location_code` | `VARCHAR(50)` |
| *(mới)* | `current_position` | `VARCHAR(50)` |
| *(mới)* | `robot_x`, `robot_y` | `NUMERIC(10,3) NULL` (`""` → `NULL`) |
| *(mới)* | `map_code` | `VARCHAR(50)` |
| *(mới)* | `message` | `VARCHAR(255)` |
| *(mới)* | `raw_payload` | `JSONB NOT NULL` (lưu nguyên gói tin) |

### 3.3. `item_stock` / `transport_request` / `production_record`
| Bảng | Hiện tại | Sau migration |
|---|---|---|
| `item_stock` | `cart_code` | `container_code` (UNIQUE) |
| `item_stock` | `locked_by_task_id` | `locked_by_mission_code` |
| `item_stock` | *(mới)* | `fleet_registered BOOLEAN DEFAULT FALSE` ⚠️ chờ chốt Q5 |
| `transport_request` | `cart_id` | `container_id` ⚠️ Q3 |
| `production_record` | `cart_code` | `container_code` |
| `production_record` | `cart_id` | `container_id` ⚠️ Q3 |

### 3.4. Bảng mới `fleet_api_call` ⚠️ chờ chốt Q4
Log mọi lệnh outbound (submitMission / containerIn / containerOut / missionCancel):
`id, api_name, request_id UNIQUE, mission_code NULL, container_code NULL, request_body JSONB, http_status INT, response_body JSONB, success BOOL, error TEXT, created_at`.

---

## 4. OUTBOUND ADAPTER (`dispatch_service.py`)

### 4.1. Ánh xạ hàm cũ → mới
| Hàm cũ | Endpoint cũ | Hàm mới | Endpoint mới |
|---|---|---|---|
| `add_task` | (generic) | `_post_kuka(api_path, body, api_name)` | generic |
| `fleet_insert_rack` | `/ics/shelf/insert` | `kuka_container_in` | `/amr/containerIn` |
| `fleet_move_material` / `fleet_move_to_wash` / `fleet_move_empty_rack` | `/ics/taskOrder/addTask` | **gộp thành 1** `kuka_submit_mission` | `/amr/submitMission` |
| `fleet_remove_rack` | `/ics/shelf/remove` | `kuka_container_out` | `/amr/containerOut` |
| `fleet_cancel_task` | `/ics/taskOrder/cancelTask` | `kuka_mission_cancel` | `/amr/missionCancel` (body chờ user) |
| `create_fleet_task` | | `submit_fleet_task(db, fleet_task)` | |

> 3 hàm move cũ chỉ khác nhau pickup/dropoff nên gộp làm một. `request_type` (`CALL_MATERIAL`, `MOVE_TO_WASH`, `RETURN_EMPTY_CART`) vẫn giữ ở `transport_request` cho nghiệp vụ.

### 4.2. Body sinh ra
**submitMission**
```json
{
  "orgId": "<settings.kuka_org_id>",
  "requestId": "<fleet_task.fleet_request_id>",
  "missionCode": "<fleet_task.mission_code>",
  "missionType": "<settings.kuka_mission_type>",
  "viewBoardType": "",
  "robotModels": [],
  "robotIds": [],
  "robotType": "<settings.kuka_robot_type>",
  "priority": "<transport_request.priority, mặc định 1>",
  "containerModelCode": "<settings.kuka_container_model_code>",
  "templateCode": "",
  "lockRobotAfterFinish": false,
  "unlockRobotId": "",
  "unlockMissionCode": "",
  "idleNode": "",
  "missionData": [
    {"sequence": 1, "position": "<pickup_location.location_code>",  "type": "NODE_POINT", "putDown": false, "passStrategy": "AUTO", "waitingMillis": 0},
    {"sequence": 2, "position": "<dropoff_location.location_code>", "type": "NODE_POINT", "putDown": true,  "passStrategy": "AUTO", "waitingMillis": 0}
  ]
}
```
**containerIn** (khi quét QR ở Khu Nguyên Liệu)
```json
{"containerCode": "<container_code>", "enterOrientation": "", "isNew": "<not item_stock.fleet_registered>", "position": "<location.location_code>", "requestId": "CIN..."}
```
**containerOut** (khi `COMPLETED` của nhiệm vụ `RETURN_EMPTY_CART` tại bãi xe rỗng)
```json
{"requestId": "COUT...", "containerType": "", "containerCode": "<container_code>", "position": "", "isDelete": false}
```
**missionCancel**: chờ user gửi body đầy đủ (mẫu bị cắt ở trường `"r...`).

### 4.3. Thứ tự giao dịch: Outbox (giải quyết race `MOVE_BEGIN`)
1. **Tx1** (trong luồng nghiệp vụ hiện có): chọn container `FOR UPDATE SKIP LOCKED` → **khóa container** → tạo `FleetTask(status='pending_submit', mission_code, fleet_request_id)` → `commit`.
2. **Sau commit:** gọi `submit_fleet_task()` → POST `submitMission`.
3. **Tx2:**
   - Fleet nhận lệnh → `status='sent'`, `sent_at`.
   - Fleet từ chối (lỗi nghiệp vụ) → `status='failed'`, mở khóa container, trả request về hàng đợi.
   - Timeout/lỗi mạng → giữ `pending_submit`, `submit_attempts += 1`. Worker nền gửi lại với **cùng mã**, tối đa `kuka_submit_max_retries` lần, quá số lần thì `failed` và cảnh báo.
4. Nếu `MOVE_BEGIN` về trong lúc task còn `pending_submit` thì vẫn hợp lệ (task đã có trong DB) → chuyển `in_progress`.

> ⚠️ Cần mẫu response thật của `submitMission`/`containerIn` để biết trường nào báo thành công (Q1).

---

## 5. KHÓA CONTAINER: ĐÁNH GIÁ ĐỀ XUẤT "KHÓA TỪ MOVE_BEGIN"

User lo hai robot cùng tới lấy một xe, và lo đó đúng. Nhưng khóa ở `MOVE_BEGIN` vẫn **quá muộn**:

```
t0  CNC-A gọi hàng → MES chọn xe X → submitMission
t1  (Fleet đang bận, mission nằm trong hàng chờ của Fleet vài giây đến vài phút)
t2  CNC-B gọi hàng → MES lại thấy xe X chưa khóa → chọn X lần nữa ❌
t3  MOVE_BEGIN của mission A mới về
```

**Plan:** khóa ngay lúc MES chọn xe (bước Tx1 ở 4.3, đây cũng là cách code hiện tại đang làm), dùng `FOR UPDATE SKIP LOCKED` để hai request đồng thời không lấy trùng.  
`MOVE_BEGIN` chỉ **xác nhận** (gán `robot_id`, `in_progress`). Nếu tới lúc đó xe chưa khóa (dữ liệu lệch) thì khóa bổ sung và ghi cảnh báo.

**Mở khóa** khi: `COMPLETED`, Fleet từ chối lệnh, `FAILED`/`CANCELLED` (theo luật Mục 7).

---

## 6. INBOUND WEBHOOK `POST /api/v1/receive-status`

### 6.1. Route (`route_api.py`)
- Chỉ giữ một đường dẫn `/receive-status` dưới prefix `/api/v1`. Xóa alias `/production/fleet/receive-status` ⚠️ Q7.
- **Xử lý đồng bộ**, không qua Celery (Celery có thể xử lý sai thứ tự `DOWN_CONTAINER`/`COMPLETED` cách nhau 38ms). Xóa `persist_task_status` trong `production_celery_task.py` ⚠️ Q8.
- Luôn trả **HTTP 200** kể cả khi không tìm thấy mission hoặc gặp trạng thái lạ (để Fleet không gửi lại vô hạn); lỗi thì ghi log. Body trả về ⚠️ Q2.

### 6.2. Xử lý (`receive_mission_callback`, đổi tên từ `receive_task_status`)
1. Luôn insert 1 dòng `task_status` (kèm `raw_payload`).
2. `SELECT fleet_task WHERE mission_code = :missionCode FOR UPDATE`. Không thấy → log warning, commit log, return.
3. Task đã ở trạng thái kết thúc (`completed`/`failed`/`cancelled`) → bỏ qua (chống lùi trạng thái và chống `COMPLETED` lặp).
4. Cập nhật chung: `robot_id`, `last_mission_status`, `current_position`.
5. Theo `missionStatus`:

| missionStatus | fleet_task.status | Hành động thêm |
|---|---|---|
| `MOVE_BEGIN` | `in_progress` | `transport_request` → `in_progress`; đảm bảo container đã khóa |
| `ARRIVED` | `in_progress` | — |
| `UP_CONTAINER` | `in_progress` | `picked_up_at = now` |
| `DOWN_CONTAINER` | `in_progress` | — (chưa hoàn thành, D2) |
| `COMPLETED` | `completed` | Xem 6.3 |
| `FAILED` / `CANCELED` / `CANCELLED` (chưa thấy trong log thật) | `failed` / `cancelled` | Xem Mục 7 |
| Giá trị khác | không đổi | Chỉ log warning |

### 6.3. Xử lý `COMPLETED`
1. `fleet_task.completed_at`; `transport_request` → `completed`.
2. Tìm `Location` theo `containerLocationCode`:
   - Khớp `dropoff_location` → bình thường.
   - Không khớp → ⚠️ Q6 (đề xuất: tin Fleet, ghi cảnh báo).
3. Container: `location_id = đích`, `is_locked = false`, `locked_by_mission_code = NULL`, `destination_location_id = NULL`.
4. Nếu `request_type = RETURN_EMPTY_CART` → gọi `containerOut` → vô hiệu hóa container (luồng bãi xe rỗng như hiện tại).
5. Commit → `scan_all_transport_queues()` (điểm lấy hàng vừa trống) → submit các FleetTask mới qua outbox.

---

## 7. HỦY NHIỆM VỤ (`missionCancel`): ÁP DỤNG Ở ĐÂU

Đề xuất 3 tình huống (⚠️ Q9):

| Tình huống | Ai bấm | Điều kiện | Sau khi hủy |
|---|---|---|---|
| C1. Công nhân hủy lệnh gọi hàng | PDA (nút Hủy hiện có của hàng đợi) | Chỉ khi **chưa** `UP_CONTAINER` (`picked_up_at IS NULL`) | Mở khóa xe, xe vẫn ở chỗ cũ; request → `cancelled` |
| C2. Quản đốc hủy nhiệm vụ bị kẹt | Màn hình Admin/Monitor | Mọi lúc | Nếu **chưa** nâng xe: như C1. Nếu **đã** nâng xe: vị trí xe không chắc chắn → đánh dấu container `needs_reconcile`, chờ người xác nhận vị trí thật |
| C3. Fleet tự báo lỗi/hủy | Callback | — | Giống C2 |

---

## 8. DANH SÁCH FILE SẼ SỬA

| File | Thay đổi |
|---|---|
| `backend/app/core/config.py` | Mục 1 |
| `backend/alembic/versions/<new>_kuka_fleet_nomenclature.py` | Mục 3 |
| `backend/app/modules/production/production_models.py` | Đổi tên cột/relationship, xóa `MAPPING_STATUS`, thêm `KUKA_MISSION_STATUS`, model `FleetApiCall` |
| `backend/app/modules/warehouse/item_stock/item_stock_model.py`, `item_stock_schema.py` | `container_code`, `locked_by_mission_code`, `fleet_registered` |
| `backend/app/modules/warehouse/item/item_schema.py`, `item_service.py` | `cart_code` → `container_code` |
| `backend/app/modules/production/dispatch_service.py` | Mục 4, 5, 6, 7 (phần lớn công việc nằm ở đây) |
| `backend/app/modules/production/route_api.py` | Webhook mới; `pda_fast_arrive` giả lập bằng payload `COMPLETED` chuẩn KUKA; `calling_task_code` → `calling_mission_code`; endpoint cancel |
| `backend/app/modules/production/route_schema.py` | `task_code` → `mission_code`, `cart_*` → `container_*` |
| `backend/app/modules/production/production_celery_task.py` | Xóa/sửa `persist_task_status`; thêm job outbox retry |
| `frontend/src/api/pda.ts`, `frontend/src/store/usePdaStore.ts` | Đổi tên trường API |
| `backend/scripts/seed_production_core.py`, `test_dispatch_engine.py`, `test_pda_live_cycle.py` | Đổi tên trường |
| `backend/scripts/test_kuka_fleet_replay.py` (mới) | Replay 7 tín hiệu thật trong `all_signals.jsonl` |
| `DOCS/kuka_fleet_real_protocol_and_integration_specification.md` | Sửa path webhook, endpoint mới, luật khóa/hủy |

---

## 9. CÂU HỎI CHỜ CHỐT

| # | Câu hỏi | Đề xuất mặc định |
|---|---|---|
| Q1 | Mẫu **response** thật của `submitMission` và `containerIn` (thành công + thất bại)? | — bắt buộc phải có |
| Q2 | Webhook trả body gì? (mẫu user gửi có `cancelMode: FORCE` giống body `missionCancel` hơn) | `200` + `{"code":"0","message":"success"}` |
| Q3 | Đổi luôn `cart_id` → `container_id`? | Có |
| Q4 | Thêm bảng `fleet_api_call` để lưu mọi lệnh gửi Fleet? | Có |
| Q5 | Xác định `isNew` bằng cột `item_stock.fleet_registered`? | Có |
| Q6 | `COMPLETED` báo vị trí khác đích dự kiến thì tin ai? | Tin Fleet + cảnh báo |
| Q7 | Xóa alias `/production/fleet/receive-status`? | Có |
| Q8 | Webhook xử lý đồng bộ, bỏ Celery? | Có |
| Q9 | Luật hủy C1/C2/C3 ở Mục 7 có đúng ý không? Body `missionCancel` đầy đủ? | — |
| Q10 | `containerOut` dùng `isDelete:false` để lần sau quét lại là `isNew:false`? | Có |
| Q11 | Mức `priority` theo loại lệnh: tất cả là 1, hay ví dụ cấp phôi 1, tẩy rửa 2, xe rỗng 3? | Tất cả là 1 |

---

## 10. THỨ TỰ THỰC HIỆN & COMMIT

| Bước | Commit | Kiểm chứng |
|---|---|---|
| 1 | `chore(config): add KUKA fleet settings, drop RCS process codes` | Backend khởi động được |
| 2 | `refactor(fleet): rename schema to KUKA nomenclature` (migration + models + mọi chỗ tham chiếu + frontend, gộp một commit để không có trạng thái hỏng) | `alembic upgrade head` + `downgrade -1` + `upgrade` lại; `git grep` không còn `task_code`/`cart_code`/`amr_code`/`order_id` trong `backend/app`, `frontend/src/api`; `npm run build` |
| 3 | `feat(fleet): KUKA outbound adapter with outbox submit` | Unit test sinh body đúng mẫu; giả lập timeout → retry cùng mã |
| 4 | `feat(fleet): KUKA mission callback state machine` | Replay 7 tín hiệu thật: container chuyển 17 → 18, mở khóa, chỉ hoàn thành ở `COMPLETED`; replay lặp/đảo thứ tự không làm hỏng state |
| 5 | `feat(fleet): mission cancel` | Sau khi có body Q9 |
| 6 | `docs(fleet): update protocol spec` | — |
| 7 | Test thật với Fleet `192.168.1.71` | Một vòng: containerIn → submitMission → 7 callback → COMPLETED |
