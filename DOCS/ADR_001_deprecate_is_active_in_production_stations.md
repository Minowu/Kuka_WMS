# ADR-001: LOẠI BỎ LOGIC IS_ACTIVE KHỎI KHỐI QUẢN TRỊ TRẠM XƯỞNG SẢN XUẤT (PRODUCTION STATIONS)

* **Trạng thái**: `ACCEPTED` (Đã phê duyệt & Áp dụng)
* **Ngày quyết định**: 2026-10-22
* **Người quyết định**: Quản đốc xưởng (User) & Lead Architecture Engineer
* **Phạm vi tác động**: Khối 1 (Trạm máy & Phân khu xưởng), Lõi điều phối AMR (Dispatch Engine)

---

## 1. BỐI CẢNH (CONTEXT)

1. Trong kiến trúc cơ sở dữ liệu KUKA WMS, bảng `location` là bảng thực thể dùng chung:
   * **Phân xưởng sản xuất**: Quản lý điểm đỗ vật lý của AMR tại 4 phân khu (`RAW_MATERIAL`, `CNC_SLOT`, `WASHING_SLOT`, `EMPTY_CART_BUFFER`).
   * **Kho tổng WMS**: Quản lý hàng trăm vị trí kệ hàng, khay chứa pallet, điểm xuất/nhập kho.
2. Ban đầu, bảng `location` có trường `is_active` (BOOLEAN, mặc định `True`).
   * Tại Kho tổng WMS: Cột này được dùng làm cơ chế **xóa mềm (soft-delete)** khi xóa một vị trí kệ kho (`location.is_active = False`) để tránh vi phạm khóa ngoại với lịch sử tồn kho và giao dịch cũ.
   * Tại Phân xưởng sản xuất (Khối 1): Trường này từng được định nghĩa trong schema `StationSlotUpdateRequest` và hiển thị trên giao diện `StationSettingPage.tsx` dưới dạng Tag xanh/xám "Hoạt động / Tạm dừng".

---

## 2. VẤN ĐỀ PHÁT SINH (THE PROBLEM)

Khi phân tích sâu vào hoạt động điều phối tự động của robot AMR và dây chuyền máy CNC:

1. **Nguy cơ phá vỡ cơ chế Đệm kép (Double Buffering POS1/POS2)**:
   * Mỗi máy CNC cần 2 vị trí đỗ: `POS1` (đón phôi vào) và `POS2` (chứa phôi hoàn thành chờ chuyển đi).
   * Nếu cho phép tắt `is_active` lắt léo ở từng slot đỗ, máy CNC bị mất đối xứng vào/ra, gây tắc nghẽn máy (Machine Starvation / Deadlock).
2. **Nguy cơ kẹt cứng phôi trung gian (WIP Trap) giữa các công đoạn CNC**:
   * Trong `dispatch_service.py`, khi máy CNC công đoạn 2 gọi phôi từ máy CNC công đoạn 1, hệ thống truy vấn các xe phôi có `Location.is_active == True`.
   * Nếu vị trí `CNC-01-POS2` bị ai đó chuyển `is_active = False`, toàn bộ các máy CNC công đoạn sau sẽ **hoàn toàn mù không nhìn thấy xe phôi này**. Hàng trăm chi tiết phôi bán thành phẩm sẽ bị **kẹt tại chỗ vĩnh viễn**, làm ngưng trệ toàn bộ dây chuyền xưởng.
3. **Thừa thãi về mặt vòng đời nghiệp vụ (Lifecycle Redundancy)**:
   * Vòng đời thực tế của một trạm xưởng được quyết định 100% bởi `location_type`:
     * Khi được gán vào xưởng $\rightarrow$ `RAW_MATERIAL`, `CNC_SLOT`, `WASHING_SLOT`, `EMPTY_CART_BUFFER`.
     * Khi giải phóng / ngừng dùng $\rightarrow$ hệ thống chuyển về **`UNASSIGNED`** (Node map tự động trở lại kho tự do).
   * Do đó, 100% trạm đang tồn tại trên xưởng đều luôn luôn là hoạt động (`is_active = True`). Cột "Trạng thái" hiển thị trên giao diện là hoàn toàn tĩnh, vô nghĩa và chiếm dụng diện tích hiển thị.

---

## 3. QUYẾT ĐỊNH KIẾN TRÚC (THE DECISION)

Chúng tôi quyết định áp dụng nguyên tắc **"Dọn sạch Khối 1, bảo toàn CSDL chung"**:

### A. Đối với Cơ sở dữ liệu (Database)
* **GIỮ NGUYÊN cột `is_active` trong bảng `location`** (mặc định luôn gán `True` khi tạo trạm).
* **Lý do**: Không chạy migration xóa cột trong DB để đảm bảo an toàn tuyệt đối, tránh làm gãy 14 file nghiệp vụ của Kho tổng WMS đang dựa vào cờ này để xóa mềm vị trí kho. Các bộ lọc bảo vệ `Location.is_active.is_(True)` trong Dispatch Engine vẫn hoạt động ổn định.

### B. Đối với Khối 1: Phân Xưởng Sản Xuất (Production)
1. **Frontend UI (`StationSettingPage.tsx`)**:
   * Xóa bỏ hoàn toàn cột "Trạng Thái" trên cả 3 bảng (Khu Cấp Phôi, Khu Tẩy Rửa, Bãi Đệm Xe Rỗng).
   * Dọn sạch các biến `is_active` thừa trong form và state.
   * Cấm hoàn toàn việc mở nút bật/tắt `is_active` trên màn hình xưởng.
2. **Backend Schemas (`station_schema.py`) & Types (`types/station.ts`)**:
   * Xóa bỏ thuộc tính `is_active` khỏi request body cập nhật trạm (`StationSlotUpdateRequest`, `StationLocationUpdateInput`).
3. **Backend Service (`station_service.py`)**:
   * Gỡ bỏ đoạn logic rườm rà kiểm tra tắt `payload.is_active is False`.

---

## 4. HỆ QUẢ & LỢI ÍCH (CONSEQUENCES)

### Điểm tích cực (Positive):
1. **Triệt tiêu 100% nguy cơ lỗi điều phối AMR**: Không còn khả năng ai đó bấm tắt nhầm một vị trí đỗ khiến xe phôi bị kẹt hoặc robot AMR đứng tắc đường giữa xưởng.
2. **Giao diện quản trị sạch và chuyên nghiệp**: Loại bỏ cột Tag tĩnh vô nghĩa, bảng thông tin trạm trở nên thoáng đãng, tập trung đúng vào: *Mã vị trí, Tên vị trí, Node bản đồ KUKA, Tọa độ thực tế (X, Y) và Thao tác*.
3. **An toàn tuyệt đối cho hệ thống**: Module Kho WMS không bị ảnh hưởng, không cần downtime DB migration.

### Hướng dẫn vận hành thay thế:
* Khi Quản đốc muốn ngừng sử dụng một vị trí trạm xưởng: Quản đốc chỉ cần bấm nút **[Xóa]** trên giao diện. Hệ thống sẽ tự động chuyển vị trí về `UNASSIGNED` để giải phóng Node bản đồ một cách sạch sẽ và chính quy.
