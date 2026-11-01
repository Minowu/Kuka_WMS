# ĐẶC TẢ KIẾN TRÚC CƠ SỞ DỮ LIỆU LÕI KUKA AMR (3NF NORMALIZED SPECIFICATION)

> Tài liệu này đã được đồng bộ với bản thiết kế chi tiết mới nhất tại [`DOCS/kuka_core_database_blueprint.md`](file:///D:/KuKA/KUKA_WMS/DOCS/kuka_core_database_blueprint.md) và [`backend/docs/kuka_core_database_blueprint.md`](file:///D:/KuKA/KUKA_WMS/backend/docs/kuka_core_database_blueprint.md) (Alembic revision `e7f8a9b0c1d2`).

## Tóm tắt Cấu trúc 22 Bảng Nghiệp vụ (3NF)
1. **Nhóm Sản phẩm & Xe phôi WIP (`item`, `item_stock`)**:
   - `item`: Danh mục Model chi tiết cơ khí (`sku`, `name`, `standard_quantity_per_cart = 120`).
   - `item_stock`: Thực thể Xe gá phôi WIP đã dọn sạch 11 cột FMCG cũ, còn đúng 14 cột (`id`, `stock_code`, `cart_code`, `item_id`, `location_id`, `destination_location_id`, `quantity`, `current_stage_level`, `is_locked`, `locked_by_task_id`, `status`, `is_active`, `created_at`, `updated_at`).
2. **Nhóm Máy CNC & Quy trình Công nghệ 3NF (`machine`, `production_route`, `route_step`, `route_step_machine`)**:
   - `machine`: Danh mục máy CNC vật lý (`CNC-01`..`CNC-04`).
   - `route_step_machine`: Bảng nối chuẩn 3NF giữa `route_step` và `machine` (thay cho mảng JSON `allowed_machines`).
3. **Nhóm Mặt bằng & Bản đồ SLAM V2 (`warehouse`, `location`, `warehouse_map`)**:
   - Đã loại bỏ hoàn toàn bảng `zone`.
   - `location`: Quản lý 23 vị trí chuẩn (`RAW_MATERIAL` 1..7, `CNC_SLOT` 4 máy $\times$ 2 vị trí `POS1`/`POS2` liên kết qua `machine_id`, `WASHING_SLOT` 1..4, `EMPTY_CART_BUFFER` 1..4) kèm tọa độ 2D (`map_x`, `map_y`).
4. **Nhóm Điều phối AMR, Hàng đợi Always-Scan & Webhook (`transport_request`, `transport_queue`, `fleet_task`, `task_status`, `production_record`)**:
   - Hỗ trợ đầy đủ cơ chế **Pull + Always-Scan (5s/lần)** cho công đoạn trung gian, **Auto-Push** sang trạm rửa ở công đoạn cuối, và **Round-Robin 1..4 + Tự xóa kệ khi hạ xe rỗng** tại `EMPTY_CART_BUFFER`.
5. **Nhóm Phân quyền & Hệ thống (`users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `user_warehouses`, `user_locations`, `notification`)**:
   - `user_locations` không giới hạn số lượng vị trí gán cho 1 tài khoản.

👉 Xem chi tiết từng trường (179 cột) và sơ đồ tuần tự biến đổi dữ liệu tại: [`DOCS/kuka_core_database_blueprint.md`](file:///D:/KuKA/KUKA_WMS/DOCS/kuka_core_database_blueprint.md).
