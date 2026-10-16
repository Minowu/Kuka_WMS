# Implementation Plan: KUKA AMR Core Database & Production Engine

## Overview
Xây dựng khối cơ sở dữ liệu cốt lõi (Core Database Architecture) và hạ tầng điều phối cho hệ thống KUKA AMR chuyển đổi từ WMS cũ sang hệ thống cấp phôi và trung chuyển WIP cho xưởng gia công cơ khí CNC.
Hệ thống kết nối trực tiếp với giao diện PDA 4.2" của công nhân tại 3 khu vực: Khu Nguyên Liệu, Khu Máy CNC (mỗi máy có 2 vị trí Vào/Ra độc lập), và Khu Tẩy Rửa (kèm Bãi đệm xe rỗng).

## Locked Architectural Constraints & Business Rules (QUY TẮC BẮT BUỘC)
> [!IMPORTANT]
> **QUY TẮC SỐ 1 VỀ MÁY CNC: 1 MÁY CNC CÓ 2 VỊ TRÍ ĐỖ XE VẬT LÝ ĐỘC LẬP**
> - Mỗi máy CNC (ví dụ `CNC-01`) trên sàn xưởng luôn có **2 vị trí đỗ xe vật lý** (`CNC01_POS1` và `CNC01_POS2`).
> - **Cả 2 vị trí đều có chức năng Vào (Infeed) và Ra (Outfeed) độc lập**:
>   + Khi vị trí TRỐNG: Công nhân bấm [GỌI PHÔI] $\rightarrow$ AMR chở xe phôi tới hạ vào vị trí này.
>   + Khi gia công xong 120 chi tiết trên xe: Công nhân bấm [BÁO XONG / UPDATE LEVEL] $\rightarrow$ AMR tới cõng xe tại vị trí này đi công đoạn tiếp hoặc sang Tẩy Rửa.
>   + Cơ chế này giúp công nhân **gia công gối đầu liên tục (Double-buffering / Zero CNC Starvation)**: đang chạy xe ở Vị trí 1 thì gọi trước xe vào Vị trí 2.
> - **Quy tắc hiển thị PDA**:
>   + Công nhân quản lý 1 máy CNC $\rightarrow$ thấy **2 thẻ vị trí**.
>   + Công nhân quản lý 2 máy CNC $\rightarrow$ thấy **4 thẻ vị trí**.

> [!IMPORTANT]
> **CÁC QUY TẮC CỐT LÕI KHÁC**
> 1. **Số lượng chi tiết trên xe gá phôi**: Cố định **120 chi tiết** (hoặc 180 theo cấu hình Model). Công nhân trên PDA quét mã QR 1 chạm, tuyệt đối không gõ số lượng.
> 2. **Hủy yêu cầu gọi xe**: Không có nút Hủy trên PDA. Chỉ Admin PC mới có quyền hủy. Nếu AMR đang di chuyển cõng xe trên đường thì không được hủy giữa đường, robot bắt buộc phải cập bến an toàn rồi mới xử lý.
> 3. **Sau Tẩy Rửa**: Công nhân bấm "Đã lấy đi rửa" (giải phóng slot) $\rightarrow$ Hệ thống tự động gửi lệnh `RETURN_EMPTY_CART` để AMR cõng xe rỗng hồi vị về **Bãi đệm xe rỗng (Empty Cart Buffer)**.
> 4. **Hai đầu cố định & Chuỗi CNC biến thiên**:
>   + Đầu vào cố định: Khu Nguyên Liệu `VT-01`..`VT-07` $\rightarrow$ sinh ra xe phôi `Level = 0`.
>   + Dây chuyền CNC ở giữa: `Level 1` đến `Level N` (quản lý bởi `production_route` & `route_step`).
>   + Đầu ra cố định: Khu Tẩy Rửa (4 Slot). Khi bước CNC cuối cùng (`is_final_cnc_step = True`) hoàn thành $\rightarrow$ AMR tự động chuyển vào slot tẩy rửa trống.

---

## Architecture Decisions & Table Schemas

### 1. Bảng vị trí `location` (Giữ nguyên cốt lõi, bổ sung trường CNC):
- `id`: PK Integer
- `location_code`: String(50) (e.g. `VT-01`..`07`, `CNC01_POS1`, `CNC01_POS2`, `CNC02_POS1`, `CNC02_POS2`... `WASH-01`..`04`, `BUF-01`..`04`)
- `location_name`: String(100) (e.g. "CNC-01 (Vị trí 1)", "CNC-01 (Vị trí 2)")
- `location_type`: String(30) (`RAW_MATERIAL`, `CNC_SLOT`, `WASHING_SLOT`, `EMPTY_CART_BUFFER`)
- `machine_code`: String(50), nullable (Gom 2 vị trí về 1 máy, ví dụ `CNC-01`)
- `position_index`: Integer, nullable (1 hoặc 2)
- `map_x`, `map_y`: Integer (Tọa độ bản đồ 2D cho AMR chạy và vẽ canvas)
- `warehouse_id`, `zone_id`, `is_active`

### 2. Bảng phân quyền vị trí `user_locations`:
- `id`: PK Integer
- `user_id`: FK `users.id`
- `location_id`: FK `location.id`
- Hỗ trợ công nhân 1 máy (gán 2 `location_id`), 2 máy (gán 4 `location_id`), nguyên liệu (gán 7 `location_id`), tẩy rửa (gán 4 `location_id`).

### 3. Bảng quy trình `production_route` & `route_step`:
- `production_route`: `id`, `name`, `item_id` (FK `item`), `version`, `is_active`
- `route_step`:
  - `id`: PK Integer
  - `route_id`: FK `production_route.id`
  - `step_number`: Integer (1, 2, 3...)
  - `stage_level`: Integer (1, 2, 3...)
  - `step_name`: String (e.g. "Phay Thô", "Phay Tinh", "Khoan Tappi")
  - `allowed_machines`: JSONB (Danh sách mã máy hợp lệ song song, ví dụ: `["CNC-01", "CNC-02"]`)
  - `is_final_cnc_step`: Boolean (Nếu True, hoàn thành sẽ tự động điều AMR sang Tẩy Rửa)

### 4. Bảng xe gá phôi `item_stock` (WIP Cart / Rack):
- Nâng cấp `item_stock`:
  - `cart_code`: String(50), unique (Mã QR xe, e.g. `RCK-1021`)
  - `item_id`: FK `item.id` (Model sản phẩm)
  - `location_id`: FK `location.id` (Vị trí vật lý hiện tại của xe)
  - `quantity`: Integer, default 120
  - `current_stage_level`: Integer, default 0 (0: Nguyên liệu thô, 1: Xong B1, 2: Xong B2...)
  - `is_locked`: Boolean, default False (Chống tranh chấp xe khi AMR đang nhận lệnh)
  - `locked_by_task_id`: String, nullable
  - `destination_location_id`: FK `location.id`, nullable

### 5. Bảng điều phối `transport_request`, `transport_queue`, `fleet_task`, `production_record`:
- `transport_request`: Yêu cầu gọi phôi / chuyển xe từ PDA hoặc tự động.
- `transport_queue`: Hàng đợi tự động khi máy gọi nhưng chưa có xe sẵn sàng, hoặc khi máy CNC cuối xong nhưng cả 4 slot Tẩy Rửa đang đầy.
- `fleet_task`: Giao tiếp với Fleet Manager (KUKA RCS).
- `production_record`: Truy xuất nguồn gốc 100% (ai bấm Báo Xong, lúc nào, máy nào, vị trí nào, mẻ nào).

---

## Task List

### Phase 1: Context Lock & Database Models
- [x] Task 1: Cập nhật tài liệu thiết kế và đặc tả locked rules (`DOCS/core_database_architecture_specification.md`) ghi nhận rõ ràng quy tắc 1 máy CNC = 2 vị trí Vào/Ra độc lập.
- [x] Task 2: Tạo SQLAlchemy Models trong `backend/app/modules/production/` và cập nhật `location_model.py`, `item_stock_model.py`, `item_model.py`.
- [x] Task 3: Tạo Alembic Migration script tạo mới các bảng và các cột bổ sung.

### Checkpoint 1: Database Foundation
- [x] Migration script chạy thành công hoặc kiểm tra syntax/ORM models hợp lệ không có xung đột.

### Phase 2: Seed Data & Dispatch Service Foundation
- [x] Task 4: Tạo Seed Data script nạp đầy đủ: 7 Models, 8 vị trí CNC (4 máy x 2 vị trí Vào/Ra), 7 vị trí Nguyên Liệu, 4 Slot Tẩy Rửa, 4 Slot Buffer, 4 Users mẫu gán quyền `user_locations`.
- [x] Task 5: Viết Service Core Dispatching: Thuật toán tìm xe gần nhất theo Euclidean 2D và logic chuyển bước/xếp hàng đợi.

### Checkpoint 2: Core Engine Ready
- [x] Seed script chạy chuẩn xác, dữ liệu nạp đầy đủ vào database.

### Phase 3: Frontend PDA Alignment
- [x] Task 6: Đồng bộ mock state trong `usePdaStore.ts` và component `CncLineModal.tsx` để phản ánh đúng 4 máy x 2 vị trí (hoặc hiển thị 2 vị trí/máy).
- [x] Task 7: Chạy kiểm thử build frontend (`npm run build`) đảm bảo 0 lỗi.

---

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Xung đột khóa ngoại với bảng Inbound/Outbound cũ trong WMS | High | Gỡ bỏ ràng buộc FK cũ trên `item_stock` và thiết kế các bảng production độc lập |
| Công nhân tại 2 máy bấm gọi cùng 1 xe phôi | High | Dùng cờ `is_locked = True` với transaction atomic trong SQLAlchemy |
| Cả 4 slot Tẩy Rửa bị đầy khi CNC cuối xong | Medium | Tự động đưa vào `transport_queue`, khi slot giải phóng thì background task kích hoạt AMR đón xe ngay |
