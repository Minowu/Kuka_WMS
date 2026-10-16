# Tasks Checklist: KUKA AMR Core Database & Production Engine

## Phase 1: Context Lock & Database Models
- [x] Task 1: Cập nhật tài liệu thiết kế và đặc tả locked rules (`DOCS/core_database_architecture_specification.md`) ghi nhận rõ ràng quy tắc 1 máy CNC = 2 vị trí Vào/Ra độc lập.
- [x] Task 2: Tạo SQLAlchemy Models trong `backend/app/modules/production/` (`production_models.py`) và cập nhật `location_model.py`, `item_stock_model.py`, `item_model.py`.
- [x] Task 3: Tạo Alembic Migration script `20261016_1500_c5e6f7a8b9d0_add_production_core_models.py` tạo mới các bảng (`user_locations`, `production_route`, `route_step`, `transport_request`, `transport_queue`, `fleet_task`, `production_record`) và các cột mới trên `location` (`machine_code`, `position_index`, `location_type`), `item_stock` (`cart_code`, `current_stage_level`, `is_locked`, `locked_by_task_id`, `destination_location_id`), `item` (`standard_quantity_per_cart`).

## Checkpoint 1: Database Foundation
- [x] Kiểm tra toàn bộ ORM Models & quan hệ khóa ngoại (Foreign Keys) không có lỗi cú pháp hoặc xung đột; Alembic upgrade chạy thành công 100%.

## Phase 2: Seed Data & Dispatch Service
- [x] Task 4: Tạo Seed Data script `backend/scripts/seed_production_core.py` nạp đầy đủ:
  - 7 Models (`MDL-01` .. `MDL-07`) với `standard_quantity_per_cart = 120`.
  - 8 vị trí CNC (4 máy x 2 vị trí Vào/Ra: `CNC01_POS1`, `CNC01_POS2`... `CNC04_POS2`).
  - 7 vị trí Nguyên Liệu (`VT-01` .. `VT-07`).
  - 4 Slot Tẩy Rửa (`WASH-01` .. `WASH-04`).
  - 4 Slot Bãi đệm xe rỗng (`BUF-01` .. `BUF-04`).
  - 4 Users mẫu và phân quyền `user_locations`.
  - Production routes mẫu cho các Model (hỗ trợ máy song song và cờ bước cuối `is_final_cnc_step`).
- [x] Task 5: Viết Core Dispatching Service (`backend/app/modules/production/dispatch_service.py`) triển khai thuật toán tính khoảng cách Euclidean 2D tìm xe gần nhất, quản lý khóa xe chống tranh chấp, xử lý gối đầu double-buffering, và tự động quản lý hàng đợi `transport_queue`.

## Checkpoint 2: Core Engine Ready
- [x] Chạy seed script và test script `test_dispatch_engine.py` thành công 100% với 7/7 test cases xanh lá.

## Phase 3: Frontend PDA Alignment & Verification
- [x] Task 6: Đồng bộ mock state trong `usePdaStore.ts` để hiển thị đúng 4 máy x 2 vị trí Vào/Ra độc lập (8 vị trí độc lập với `positionIndex: 1 | 2`), hiển thị badge vị trí trên `CncLineModal.tsx`.
- [x] Task 7: Chạy kiểm thử frontend build (`npm run build`) và verify 0 lỗi.
