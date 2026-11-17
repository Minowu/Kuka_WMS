# KUKA Fleet webhook & mission protocol

Tài liệu thay thế `legacy_wms_archive/robot/` (đã xóa ở mức Clean Architecture C).

## Endpoint hiện tại

- **Inbound webhook:** `POST /api/v1/receive-status` (production fleet router)
- **Worker:** Celery task `robot.persist_task_status` → `HandleWebhookUseCase` → `WebhookHandler.receive_task_status`
- **Outbound submit:** Celery `production.submit_fleet_task` → `SubmitTaskUseCase` → `IFleetSubmitter` → `/amr/submitMission`

## Payload webhook (canonical)

| Field (ưu tiên) | Alias chấp nhận | Ý nghĩa |
|---|---|---|
| `missionCode` | `mission_code`, `orderId` | Mã nhiệm vụ Fleet / WMS |
| `missionStatus` | `mission_status`, `status` | Trạng thái thô từ ICS/RCS |
| `robotId` | `robot_id`, `deviceCode` | ID AMR |
| `containerCode` | `container_code`, `shelfNumber` | Mã xe/rack |
| `containerLocationCode` | | Vị trí container trên map Fleet |
| `currentPosition` | | Vị trí hiện tại |
| `mapCode` | | Mã map |
| `orgId` | | Org Fleet |
| `message` | | Thông báo lỗi/ghi chú |
| `robotX` / `robotY` | | Tọa độ (optional) |

Phản hồi API thành công: `{ "code": 0 }` (worker path) hoặc theo router fleet.

## Ánh xạ trạng thái mission (production)

Nguồn: `FLEET_MISSION_STATUS` / `MAPPING_STATUS` trong
`app.infrastructure.persistence.sqlalchemy.models.production_orm`.

| ICS/RCS status | WMS `FleetTask.status` |
|---|---|
| `MOVE_BEGIN`, `ARRIVED`, `UP_CONTAINER`, `DOWN_CONTAINER` | `in_progress` |
| `COMPLETED` | `completed` |
| `FAILED`, `ABORTED`, `ABORT`, `EXCEPTION`, `TERMINATED`, `TIMEOUT` | `failed` |
| `CANCELED`, `CANCELLED`, `CANCEL` | `cancelled` |

Chỉ `COMPLETED` mới chạy `complete_fleet_task` (đổi vị trí cart, containerOut nếu trả xe rỗng).

## Legacy robot archive (đã deprecate)

Giao thức cũ dùng `orderId` + bảng `robot_task` gắn inbound/outbound (đã xóa).
Mapping số cũ (`"6"→in_progress`, `"8"→completed`, …) **không còn dùng** — production dùng tên trạng thái chuỗi như bảng trên.

## Luồng submit 3 bước (worker)

1. CAS `pending_submit → submitting`, đọc pickup/dropoff, build payload, commit, đóng DB
2. HTTP POST `/amr/submitMission` (không giữ DB)
3. Ghi `FleetApiCall`, CAS `submitting → sent` (hoặc retry / `fail_and_release`)
