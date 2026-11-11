# Audit Log / Action Log — API Contract (FE integration)

Base URL: `/api/v1` · Auth: `Authorization: Bearer <access_token>` · Thời gian: ISO-8601 có múi giờ (UTC từ server).

## 1. Header FE phải gửi

| Header | Bắt buộc | Giá trị | Ghi chú |
|---|---|---|---|
| `X-Request-ID` | Có (đã có sẵn) | UUID | Nối 1 dòng log DB với log chi tiết trong Loki |
| `X-Client-Type` | Có | `pda` \| `tv` \| `desktop` | FE suy ra từ route (`/pda/*`, `/tv*`, còn lại). Chỉ dùng khi IP **chưa** được đăng ký trong bảng thiết bị |

`device_name` **không** do FE gửi: backend tự tra từ IP thật của thiết bị qua bảng `devices` (mục 5).

## 2. Hệ thống ghi gì, khi nào

### Audit log (`audit_logs`) — không lưu payload

| `event_type` | Khi nào | `result` | `failure_reason` có thể có |
|---|---|---|---|
| `LOGIN` | `POST /auth/login` | `SUCCESS` / `FAILED` | `USER_NOT_FOUND`, `WRONG_PASSWORD` |
| `LOGOUT` | `POST /auth/logout` | `SUCCESS` | — |
| `PERMISSION_DENIED` | Bất kỳ API nào trả 403 khi đã có token | `FAILED` | `INSUFFICIENT_PERMISSION`, `INACTIVE_USER` |
| `TOKEN_INVALID` | Token sai chữ ký / sai loại / user đã bị xoá. **Token hết hạn KHÔNG ghi** | `FAILED` | `INVALID_SIGNATURE`, `INVALID_CLAIMS`, `WRONG_TOKEN_TYPE`, `MALFORMED`, `MISSING_SUBJECT`, `USER_NOT_FOUND` |

### Action log (`action_logs`)

Ghi khi **đồng thời**: method ∈ `POST/PUT/PATCH/DELETE` · đã xác định được user · path không thuộc danh sách loại trừ:
`/auth/login`, `/auth/refresh`, `/auth/logout` (đã có audit), `/logs/client`, `/production/fleet/receive-status` (đã có bảng `task_status`).

- Ghi cả request thất bại sau khi xác thực (400/403/404/409/422/500). Không ghi 401.
- `payload` đã che: `password`, `password_confirm`, `token`, `refresh_token`, `access_token`, `secret`, `authorization` → `"***"`. Tối đa ~8000 ký tự, vượt thì trả `{"_truncated": true, "preview": "..."}`. Upload file → `{"_multipart": true, "size_bytes": n}`.
- `action` = tên hàm endpoint backend (vd `call_material`, `update_user`).

## 3. `GET /audit-logs`

Quyền: `audit:read`.

Query params (đều tuỳ chọn):

| Param | Kiểu | Mô tả |
|---|---|---|
| `page` | int ≥ 1 | Mặc định 1 |
| `page_size` | int 1–100 | Mặc định 20 |
| `date_from`, `date_to` | ISO datetime | Bao gồm 2 đầu |
| `username` | string | Chứa, không phân biệt hoa thường |
| `result` | `SUCCESS` \| `FAILED` | |
| `ip` | string | Khớp chính xác |
| `device_name` | string | Chứa, không phân biệt hoa thường |
| `event_type` | `LOGIN` \| `LOGOUT` \| `PERMISSION_DENIED` \| `TOKEN_INVALID` | |

Response `200`:

```json
{
  "items": [
    {
      "id": 7,
      "event_type": "PERMISSION_DENIED",
      "result": "FAILED",
      "failure_reason": "INSUFFICIENT_PERMISSION",
      "user_id": 2,
      "username": "operator_cnc_01",
      "ip": "192.168.50.31",
      "user_agent": "Mozilla/5.0 (Linux; Android 11) ...",
      "device_type": "pda",
      "device_name": "PDA-CNC-01",
      "request_id": "67f0beeb4754447db08bbb29298c3d6c",
      "path": "/api/v1/audit-logs",
      "created_at": "2026-11-10T15:25:04.631Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

## 4. `GET /action-logs`

Quyền: `audit:read`. Nhận toàn bộ params chung của mục 3 (trừ `event_type`), thêm:

| Param | Kiểu | Mô tả |
|---|---|---|
| `action` | string | Chứa, không phân biệt hoa thường |
| `method` | `POST` \| `PUT` \| `PATCH` \| `DELETE` | |
| `resource_type` | string | Khớp chính xác (vd `users`, `devices`, `racks`) |

Response `200`:

```json
{
  "items": [
    {
      "id": 2,
      "user_id": 1,
      "username": "admin",
      "action": "signup",
      "method": "POST",
      "route_template": "/api/v1/auth/signup",
      "path": "/api/v1/auth/signup",
      "resource_type": "auth",
      "resource_id": null,
      "status_code": 201,
      "result": "SUCCESS",
      "error_message": null,
      "payload": { "username": "op01", "email": "op01@kuka.com", "password": "***", "password_confirm": "***" },
      "query_params": null,
      "duration_ms": 312,
      "ip": "192.168.50.10",
      "device_type": "desktop",
      "device_name": null,
      "request_id": "0b6c...",
      "created_at": "2026-11-10T15:25:04.120Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

`resource_type` / `resource_id`: lấy từ route template — `/api/v1/users/{user_id}` → `users` / `"12"`. Route không có path param → `resource_type` = đoạn đầu tiên sau `/api/v1`, `resource_id = null`.

## 5. Bảng thiết bị (ánh xạ IP tĩnh → tên)

| Method | Path | Quyền | Body | Response |
|---|---|---|---|---|
| GET | `/devices` | `audit:read` | — | `Device[]` |
| POST | `/devices` | `device:manage` | `DeviceCreate` | `201 Device` · `409` nếu IP đã tồn tại · `422` nếu IP sai định dạng |
| PATCH | `/devices/{device_id}` | `device:manage` | `DeviceUpdate` (mọi field tuỳ chọn) | `200 Device` · `404` · `409` |
| DELETE | `/devices/{device_id}` | `device:manage` | — | `204` · `404` |

```json
// DeviceCreate
{ "ip_address": "192.168.50.31", "name": "PDA-CNC-01", "device_type": "pda", "description": "Máy CNC line 1", "is_active": true }

// Device
{ "id": 1, "ip_address": "192.168.50.31", "name": "PDA-CNC-01", "device_type": "pda",
  "description": "Máy CNC line 1", "is_active": true,
  "created_at": "2026-11-10T15:25:04Z", "updated_at": "2026-11-10T15:25:04Z" }
```

- Thay đổi thiết bị có hiệu lực trong log sau tối đa 60 giây (cache trong process).
- `device_name` trong log là **ảnh chụp tại thời điểm ghi**, đổi tên thiết bị không sửa log cũ.

## 6. Thay đổi Auth liên quan

| API | Thay đổi |
|---|---|
| `POST /auth/logout` (mới) | Cần Bearer token · `204`. Chỉ ghi audit — JWT không bị thu hồi, token vẫn dùng được tới khi hết hạn |
| `POST /auth/signup` | **Bắt buộc** Bearer token có quyền `user:create` (trước đây không cần đăng nhập). Không token → `403 Not authenticated` |

FE: gọi `POST /auth/logout` **trước** khi xoá token (fire-and-forget, không chặn UI); không gắn tự động token / không retry-refresh cho `/auth/logout`.

## 7. Enum tham chiếu

```ts
type AuditEventType = 'LOGIN' | 'LOGOUT' | 'PERMISSION_DENIED' | 'TOKEN_INVALID';
type LogResult = 'SUCCESS' | 'FAILED';
type DeviceType = 'pda' | 'tv' | 'desktop';
type ActionMethod = 'POST' | 'PUT' | 'PATCH' | 'DELETE';
```

## 8. Thời gian lưu

Celery beat chạy 02:00 hằng ngày (`audit.cleanup_expired_logs`):
`AUDIT_LOG_RETENTION_DAYS=180`, `ACTION_LOG_RETENTION_DAYS=90` (đổi qua biến môi trường).

## 9. FE đã tích hợp

Route `/setting/audit-logs` (menu "Cài đặt hệ thống → Nhật ký hệ thống"), 2 tab:
- **Đăng nhập & bảo mật** → `GET /audit-logs`
- **Thao tác nghiệp vụ** → `GET /action-logs` (mở rộng dòng để xem payload, query, lỗi, request_id)

File: `pages/AuditLogPage.tsx`, `pages/components/auditLog/*`, `hooks/useAuditLogs.ts`, `hooks/useLogFilters.ts`, `api/auditLog.ts`, `types/auditLog.ts`, `constants/auditLog.ts`, `utils/clientType.ts`.
