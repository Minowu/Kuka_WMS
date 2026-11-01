# Danh Sách Công Việc Cần Thực Hiện (Task List)

## Phase 1: Gỡ bỏ `default_stage_level` & Chuẩn hóa CSDL
- [x] **Task 1.1**: Tạo migration Alembic gỡ bỏ cột `default_stage_level` khỏi bảng `location` và `machine` (`20261019_1935_c3d4e5f6a7b8`).
- [x] **Task 1.2**: Cập nhật backend models (`location_model.py`, `production_models.py`), schemas (`machine_schema.py`) và router.
- [x] **Task 1.3**: Làm sạch dữ liệu: Xóa các vị trí mock ảo tự sinh, liên kết lại các vị trí thực tế với các Node từ file map KUKA (`map_CNC001_CNC001_28s.json`).

## Checkpoint 1: Database Clean & Migration Head
- [x] `alembic upgrade head` chạy thành công (head: `c3d4e5f6a7b8`).
- [x] Không còn `default_stage_level` trong CSDL.

---

## Phase 2: Xây dựng Trang Hợp nhất "Cấu Hình Trạm & Phân Khu Xưởng" (`/production/stations`)
- [x] **Task 2.1**: Backend API quản lý vị trí theo phân khu:
  - CRUD ô nguyên liệu (`location_type = 'RAW_MATERIAL'`).
  - CRUD máy CNC và các vị trí đỗ linh hoạt 1..3 slots (`POS1`, `POS2`, `POS3`) liên kết với Node map.
  - CRUD slot tẩy rửa (`location_type = 'WASHING_SLOT'`) và slot đệm xe rỗng (`EMPTY_CART_BUFFER`).
  - API lấy danh sách các Node điểm đỗ có sẵn từ Map (`/api/v1/production/map/available-nodes`).
- [x] **Task 2.2**: Xây dựng giao diện trang `/production/stations` (StationSettingPage) với 3 Tab:
  - Tab 1: **Khu Cấp Phôi** (Danh sách ô, nút Thêm ô, chọn Node map kèm tọa độ x, y).
  - Tab 2: **Khu Máy CNC** (Danh sách máy, nút Thêm máy, cấu hình 1..3 slot POS1/POS2/POS3 chọn Node map, không có `default_stage_level`).
  - Tab 3: **Khu Tẩy Rửa & Bãi Đệm** (Danh sách slot rửa và bãi đệm, chọn Node map).
- [x] **Task 2.3**: Cập nhật menu Sidebar và Router chuyển từ `/machines` sang `/production/stations` (kèm alias redirect mượt mà).

## Checkpoint 2: Quản trị Vị trí Hoàn chỉnh
- [x] Quản đốc có thể thêm/sửa/xóa ô nguyên liệu, máy CNC (1..3 slot) và ô tẩy rửa, tất cả đều gắn với Node thật của Map KUKA.

---

## Phase 3: Tái cấu trúc Phân Quyền Người Dùng 1 Khu Vực (User Area Assignment)
- [x] **Task 3.1**: Cập nhật Backend API phân quyền `/api/v1/production/users/{user_id}/locations`:
  - Hỗ trợ lưu danh sách vị trí phân quyền cho user.
  - Tự động xóa các vị trí thuộc khu vực khác khi user được gán khu vực mới.
- [x] **Task 3.2**: Thiết kế lại toàn bộ `StationAssignmentModal.tsx`:
  - Radio/Segmented chọn 1 trong 3 khu vực: `[Khu Cấp Phôi]` | `[Khu Gia Công CNC]` | `[Khu Tẩy Rửa]`.
  - Nếu chọn Khu Cấp Phôi: Hiện các ô phôi (`VT-01..07`) để tick chọn.
  - Nếu chọn Khu Tẩy Rửa: Hiện các slot rửa (`WASH-01..04`) để tick chọn.
  - Nếu chọn Khu CNC: Hiện các Máy CNC trong xưởng (`CNC-01`, `CNC-02`...) để tick chọn máy (chọn máy nào tự động gán toàn bộ slot của máy đó).
- [x] **Task 3.3**: Cập nhật Client PDA (`RoleHomeRedirect.tsx`, `usePdaStore.ts`, các trang PDA):
  - Khi công nhân đăng nhập: Tự động điều hướng vào đúng trang của khu vực.
  - Lọc realtime: PDA chỉ hiển thị đúng các ô / trạm máy mà tài khoản có quyền.

## Checkpoint 3: Phân Quyền 1 Khu Vực Hoạt Động Mượt Mà
- [x] Thao tác phân quyền trên web lưu chính xác.
- [x] Đăng nhập PDA kiểm tra lọc đúng các trạm.

---

## Phase 4: Kiểm thử Toàn diện & Tự động hóa Trình duyệt
- [x] **Task 4.1**: Cập nhật bộ test backend `test_dispatch_engine.py` (14/14 pass) và `test_pda_live_cycle.py` (10/10 steps pass).
- [x] **Task 4.2**: Chạy kiểm thử tự động Playwright trên Chrome thực tế (`scratch/test_browser_phase4.py`):
  - Đăng nhập Admin thành công.
  - Trang Cấu hình Trạm 3 Tab hiển thị chuẩn xác, không còn `default_stage_level`.
  - Modal Phân quyền chuyển đổi mượt mà 3 phân khu, không lỗi JavaScript runtime.
  - Cả 3 giao diện PDA (CNC, Nguyên Liệu, Tẩy Rửa) tải thành công 100%.
- [x] **Task 4.3**: Chạy `npm run build` frontend hoàn thành trong 763ms với 0 lỗi TypeScript.
