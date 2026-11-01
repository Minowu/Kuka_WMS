# TÀI LIỆU GIẢI PHẪU CHI TIẾT CÁC MODULE ĐÃ TÁCH BỎ (`legacy_wms_archive` REFERENCE)

> **Mục đích tài liệu**: Giải phẫu chi tiết toàn bộ **6 module cũ** đã được chuyển vào `backend/legacy_wms_archive/` (`robot`, `inbound_order`, `outbound_order`, `transaction_history`, `stocktake`, `unit`). Tài liệu liệt kê **từng file, từng hàm cụ thể trước đây làm gì, cơ chế lock/vận chuyển cũ nằm ở đâu**, và đánh giá **cái gì nên bỏ hẳn, cái gì nên rút lõi để tái sử dụng** giúp bạn tự tin đánh giá và làm chủ toàn bộ hệ thống.

---

## 1. TỔNG QUAN 6 MODULE TRONG `backend/legacy_wms_archive/`

| STT | Thư mục Module | Các bảng DB liên quan | Mục đích trong WMS cũ (Masan FMCG) | Đánh giá giá trị tái sử dụng |
|:---:|:---|:---|:---|:---|
| 1 | **`robot/`** | `robot_task`, `task_status` | Bắn lệnh HTTP xuống RCS (`:7000/ics/taskOrder/addTask`) và nhận Webhook Callback từ robot qua Celery. | **RẤT CAO (CẦN RÚT LÕI)**: Cần lấy cơ chế HTTP Client + Celery Retry + Webhook Callback sang gắn vào `FleetTask` mới. |
| 2 | **`inbound_order/`** | `inbound_order`, `inbound_order_detail`, `inbound_order_allocation` | Tạo đơn nhập kho, gợi ý ô trống (khoá tạm qua Redis), tạo pallet `in_transit`, gọi robot cất hàng vào kệ. | **TRUNG BÌNH (THAM KHẢO)**: Bỏ bảng đơn hàng, chỉ tham khảo cách tạo task đường đi `taskPath: "start,target"` và dọn sạch tàn dư Redis cache. |
| 3 | **`outbound_order/`** | `outbound_order`, `outbound_order_detail`, `outbound_order_allocation` | Tạo đơn xuất kho, phân bổ tồn kho theo FEFO/Lot, gọi robot lấy pallet ra trạm, tạo lệnh trả kệ dư (`return`). | **THẤP - TRUNG BÌNH**: Nghiệp vụ xuất lẻ/FEFO không dùng cho CNC, chỉ tham khảo cách chặn vị trí đang `in_transit` và cách tạo lệnh trả ngược (`return`). |
| 4 | **`transaction_history/`** | `transaction`, `history` | Lưu sổ cái dịch chuyển tồn kho (`from_location` $\rightarrow$ `to_location`) và lịch sử đổi trạng thái đơn Nhập/Xuất. | **THẤP (ĐÃ THAY THẾ)**: Đã được thay bằng `ProductionRecord` (lịch sử gia công) và `TransportRequest` / `FleetTask` (lịch sử di chuyển). |
| 5 | **`stocktake/`** | `stocktake`, `stocktake_item` | Lập phiếu kiểm kê kho định kỳ, đếm số lượng thực tế so với sổ sách và chốt lệch (`discrepancy`). | **KHÔNG DÙNG (BỎ HẲN)**: Xưởng CNC quản lý theo xe phôi WIP thời gian thực, không kiểm kê tồn kho kiểu kho hàng. |
| 6 | **`unit/`** | `unit`, `item_unit` | Danh mục đơn vị tính (Thùng, Hộp, Gói, Pallet) và bảng hệ số quy đổi (`conversion_factor`). | **KHÔNG DÙNG (BỎ HẲN)**: Xưởng CNC đếm theo số lượng phôi chuẩn trên xe (`standard_quantity_per_cart`), không quy đổi thùng/gói. |

---

## 2. GIẢI PHẪU CHI TIẾT TỪNG MODULE & TỪNG HÀM ĐÃ BỎ

---

### 2.1. Module `robot/` ([`backend/legacy_wms_archive/robot/`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot)) — **QUAN TRỌNG NHẤT**

Đây là module giao tiếp trực tiếp với hệ thống điều khiển robot (RCS/ICS).

#### A. File [`robot_model.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_model.py)
- **`MAPPING_STATUS`**: Từ điển ánh xạ mã trạng thái số từ RCS trả về sang chữ:
  - Ví dụ: `"6"` hoặc `"8"` $\rightarrow$ `"completed"`, các mã đang chạy $\rightarrow$ `"in_progress"`, mã lỗi $\rightarrow$ `"failed"`.
- **Bảng `RobotTask`**: Lưu `order_id`, `process_code`, `system_code`, `task_order_detail` (chuỗi JSON `[{"taskPath": "start,target"}]`), nhưng bị thiết kế dính cứng cột `inbound_order_detail_id` vào đơn nhập kho.
- **Bảng `TaskStatus`**: Lưu log từng gói tin webhook mà RCS bắn về (`order_id`, `sub_task_status`, `device_code`, `qr_code`, `shelf_number`, `status`).

#### B. File [`robot_service.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_service.py) — Class `TaskStatusService`
1. **[`add_task(self, payload: dict) -> dict` (dòng 29–41)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_service.py#L29-L41)**:
   - Dùng `httpx.Client(timeout=5.0)` gửi `POST` tới `{settings.kuka_base_url}:7000/ics/taskOrder/addTask`.
   - Nếu lỗi HTTP $\ge 500$ hoặc mất kết nối mạng $\rightarrow$ Ném ngoại lệ `IcsError(..., retryable=True)` để Celery tự động thử lại (retry).
2. **[`create_robot_task(self, db: Session, task: RobotTask, not_inserted: bool = True)` (dòng 43–59)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_service.py#L43-L59)**:
   - Đóng gói dữ liệu chuẩn gửi xuống RCS:
     ```python
     payload = {
         "orderId": task.order_id,
         "modelProcessCode": task.process_code,
         "fromSystem": task.system_code,
         "taskOrderDetail": json.loads(task.task_order_detail),  # [{"taskPath": "A,B"}]
     }
     ```
   - Gọi `self.add_task(payload)`, nếu gửi thành công mới `db.commit()` lưu task.
3. **[`_settle_inbound_stock(self, db: Session, detail: InboundOrderDetail)` (dòng 61–105)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_service.py#L61-L105)**:
   - Khi lệnh robot của đơn nhập kho hoàn thành:
     - Tìm các `ItemStock` thuộc `detail.id`.
     - **Đổi vị trí**: `stock.location_id = detail.to_location_id`.
     - **Mở trạng thái**: `stock.status = "available"` (trước đó khi đang chạy là `"in_transit"`).
     - Ghi dòng `Transaction` và `History`.
4. **[`receive_task_status(self, db: Session, payload: dict)` (dòng 107–175)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_service.py#L107-L175)**:
   - Hàm xử lý khi RCS gọi Webhook báo trạng thái robot:
     - Tìm `RobotTask` theo `orderId`. Nếu đã `"completed"` rồi thì bỏ qua (Idempotency chống xử lý trùng).
     - **Điểm hạn chế trong code cũ (dòng 119–125)**: Bắt buộc `robot_task` phải gắn với `inbound_order_detail_id` hoặc `outbound_order_allocations`, nếu không có sẽ báo lỗi `ValueError("Order not found")`.
     - Khi trạng thái RCS ánh xạ sang `"completed"`:
       - Nếu là Inbound: gọi `_settle_inbound_stock` để chuyển `stock.location_id = detail.to_location_id`.
       - Nếu là Outbound: đổi `allocation.status = "pre_completed"` (chờ công nhân xác nhận lấy hàng) và chuyển tất cả `stock.location_id` từ `from_location` sang `to_location` (dòng 148–156).
     - Lưu bản ghi log vào bảng `TaskStatus`.

#### C. File [`robot_celery_task.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_celery_task.py)
- **[`persist_task_status(self, payload: dict)` (dòng 9–34)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/robot/robot_celery_task.py#L9-L34)**:
  - Celery task chạy nền nhận webhook từ RCS, cấu hình `max_retries=3`, `acks_late=True`, tự động retry theo hàm mũ `countdown = 5 * (2 ** retries)` nếu DB đang bận.

> [!IMPORTANT]
> **Đánh giá cho bạn**: Module `robot/` này chứa giao thức thật (`:7000/ics/taskOrder/addTask`, cấu trúc `taskPath: "start,target"`, và webhook callback `receive_task_status`). Bạn **nên giữ lại cơ chế giao tiếp này** và gắn nó thẳng vào bảng `FleetTask` + `DispatchService` của hệ thống mới!

---

### 2.2. Module `inbound_order/` ([`backend/legacy_wms_archive/inbound_order/`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order))

Module này trước đây phục vụ quy trình Nhập kho hàng tiêu dùng từ nhà cung cấp.

#### Giải phẫu các hàm chính trong [`inbound_order_service.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py):
1. **[`suggest_allocation_inbound(db, body)` (dòng 69–140)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py#L69-L140)** — **Cơ chế Lock tạm bằng Redis khi gợi ý ô trống**:
   - Quét các key Redis `inbound:reserved:*` để lấy danh sách `location_id` đang được giữ chỗ tạm trên màn hình tạo đơn.
   - Query bảng `Location` tìm các ô có `Location.status == "empty"` và không nằm trong danh sách Redis `inbound:reserved:*`.
   - Sau khi chọn được ô trống, ghi vào Redis: `cache_set(f"inbound:reserved:{location.id}", ...)` để người khác không được gợi ý trùng ô đó nữa.
2. **[`delete_allocated_locations(location_ids)` (dòng 148–152)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py#L148-L152)**:
   - Xóa key Redis `inbound:reserved:{location_id}` khi người dùng hủy hoặc đổi ô trên giao diện.
3. **[`_create_stock_and_allocation(db, detail, payload)` (dòng 155–233)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py#L155-L233)**:
   - Khi lưu chi tiết đơn nhập, hàm này tạo sẵn một bản ghi `ItemStock` đặt tại vị trí đầu vào (`location_id = detail.from_location_id`) với trạng thái **`status = "in_transit"`** (hoặc `"split"` nếu là hàng lẻ), gắn với mã tem `QR_Code`, và tạo dòng `InboundOrderAllocation`.
4. **[`_create_detail_with_stock_and_allocation(db, order, line, inbound_type)` (dòng 640–670)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py#L640-L670)**:
   - Tạo `InboundOrderDetail` có `from_location_id` và `to_location_id`, tạo `ItemStock` + `InboundOrderAllocation`, rồi xóa khóa tạm Redis `cache_delete(f"inbound:reserved:{line.to_location_id}")`.
5. **[`execute_inbound_task(db, detail_id)` (dòng 753–844)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py#L753-L844)**:
   - Nếu `detail_type == "manual"` (kho thủ công): Đổi thẳng `stock.status = "available"` và ghi `Transaction`.
   - Nếu là kho tự động (Robot):
     - Lấy `start = detail.from_location.location_code`, `target = detail.to_location.location_code`.
     - Tạo `RobotTask` với `task_order_detail = json.dumps([{"taskPath": f"{start},{target}"}])`.
     - Gọi `task_status_service.create_robot_task(db, robot_task)` để bắn lệnh xuống robot và đổi `detail.status = "issued"`.
6. **[`caller_inbound_order(db, body, user_id, inbound_type)` (dòng 902–929)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/inbound_order_service.py#L902-L929)**:
   - Hàm gộp "Tạo đơn nhập + Bắn lệnh robot ngay lập tức" khi công nhân thao tác trên PDA (tạo đơn xong lặp qua từng `detail` gọi `execute_inbound_task`).
7. **File [`qr_code_module.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/inbound_order/qr_code_module.py)**:
   - Quét QR trên PDA để gán tạm kiện hàng vào vị trí đầu vào thông qua Redis key `inbound:assign:location:{location_id}:{qr_code_id}` trước khi bấm tạo đơn.

> [!NOTE]
> **Đánh giá cho bạn**:
> - Ở hệ thống cũ, để di chuyển 1 kệ từ A sang B phải đi vòng qua 3 bảng (`InboundOrder` $\rightarrow$ `InboundOrderDetail` $\rightarrow$ `InboundOrderAllocation`) + tạo tem `QR_Code` + lưu tạm Redis `inbound:assign:*` và `inbound:reserved:*`.
> - Ở hệ thống mới, bạn chỉ cần `TransportRequest` + `FleetTask` và khóa trực tiếp trên `ItemStock` (`is_locked = True`, `destination_location_id = B`). Nhẹ hơn và trực diện hơn rất nhiều!

---

### 2.3. Module `outbound_order/` ([`backend/legacy_wms_archive/outbound_order/`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order))

Module này trước đây phục vụ quy trình Xuất kho theo đơn đặt hàng (chọn hàng theo hạn sử dụng FEFO, kiểm tra Lot, lấy nguyên pallet hoặc lấy lẻ rồi trả kệ dư về kho).

#### Giải phẫu các hàm chính trong [`outbound_order_service.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order/outbound_order_service.py):
1. **[`create_outbound_order(db, body, user_id)` (dòng 150–213)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order/outbound_order_service.py#L150-L213)**:
   - Tạo đơn xuất kho `OutboundOrder` và các dòng `OutboundOrderDetail` (hỗ trợ các loại đơn đặc thù Masan: `"Tuyển chọn"`, `"Lấy lỗi"`, `"Lấy lẻ"`).
2. **[`calculate_outbound_order` & `greedy_allocate_stocks_to_lines` (dòng 645–762)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order/outbound_order_service.py#L645-L762)**:
   - Tìm các `ItemStock` trong kho có `available_quantity > 0` theo chiến thuật FEFO/Lot (`_strategy_loading_stocks`).
   - Phân bổ số lượng cần lấy vào bảng `OutboundOrderAllocation` và tạo sẵn bản ghi `RobotTask` ở trạng thái `"initialize"` (lúc này `taskPath` để `"None"` vì chưa biết công nhân đứng ở trạm xuất nào).
   - **Cách khóa tồn kho của Outbound cũ**: Không dùng cột `is_locked`, mà dùng subquery `ItemStock.available_quantity = quantity - SUM(OutboundOrderAllocation.quantity)`. Khi một `ItemStock` đã bị gắn vào `OutboundOrderAllocation`, `available_quantity` của nó giảm xuống = 0 để đơn xuất khác không bốc trùng.
3. **[`execute_outbound_task(db, body, detail_type)` (dòng 1157–1287)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order/outbound_order_service.py#L1157-L1287)** — **Chỗ kiểm tra Lock vị trí nguồn và tạo lệnh trả kệ dư**:
   - Kiểm tra vị trí lấy hàng (`start = Location`):
     - Nếu `start.status == "empty"` $\rightarrow$ Báo lỗi không có hàng.
     - Nếu `start.status == "in_transit"` $\rightarrow$ Báo lỗi đang có robot khác chạy tại vị trí này.
     - Kiểm tra `body.from_location_id != stock.location_id` (dòng 1219): Chống trường hợp pallet đã bị lệnh khác dời đi.
   - Điền đường đi thật vào `RobotTask`: `task_path = f"{start.location_code},{target.location_code}"`.
   - **Logic trả kệ dư (dòng 1241–1267)**: Nếu trên kệ có 100 thùng (`full_quantity = 100`) mà đơn xuất chỉ lấy 30 thùng (`taken = 30`), hệ thống tự động tạo sẵn 1 `RobotTask` chiều về (`TDS_Return_...`, `taskPath = f"{target.location_code},{start.location_code}"`) và 1 dòng `OutboundOrderAllocation(allocation_type="return", quantity=70)` để sau khi công nhân nhặt 30 thùng xong thì bấm gọi robot chở 70 thùng còn lại về chỗ cũ!
   - Gọi `task_status_service.create_robot_task` gửi lệnh xuống RCS.
4. **[`_settle_outbound_stock(db, allocations)` (dòng 1289–1366)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order/outbound_order_service.py#L1289-L1366)** & **[`confirm_outbound_order` / `confirm_no_qr` (dòng 1368–1415)](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/outbound_order/outbound_order_service.py#L1368-L1415)**:
   - Sau khi robot mang kệ ra vị trí xuất (`allocation.status == "pre_completed"`), công nhân quét QR xác nhận đã lấy hàng $\rightarrow$ Trừ tồn kho `stock.quantity -= allocation.quantity`, đổi `allocation.status = "completed"`, và ghi `Transaction` + `History`.

> [!TIP]
> **Đánh giá cho bạn**:
> - Toàn bộ logic chia lẻ thùng hàng (`split`), lọc hạn sử dụng (`FEFO`), tuyển chọn/lấy lỗi là nghiệp vụ kho hàng FMCG, bỏ đi là hoàn toàn đúng.
> - Riêng ý tưởng **"sau khi lấy hết hàng trên kệ tại trạm đích, điều robot chở kệ/xe rỗng quay về bãi"** của Outbound cũ hiện đã được viết lại gọn hơn nhiều trong hàm [`DispatchService.release_wash_slot_and_return_empty`](file:///D:/Cty_sptech/kuka/backend/app/modules/production/dispatch_service.py#L470-L601)!

---

### 2.4. Module `transaction_history/` ([`backend/legacy_wms_archive/transaction_history/`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/transaction_history))

- **[`history_service.py`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/transaction_history/history_service.py)**:
  - `list_transactions`, `create_transaction`: Ghi và đọc bảng `transaction` (`from_location_id`, `to_location_id`, `item_stock_id`, `quantity`, `transaction_type`).
  - `list_histories`, `create_history`: Ghi và đọc bảng `history` gắn với `inbound_order_id` và `outbound_order_id`.
  - `get_transaction_history(db, qr_code, order_code)`: Tra cứu lịch sử đường đi của 1 mã QR hoặc 1 mã đơn hàng.
- **Tại sao bỏ**: Bảng `History` bị trói chặt vào `inbound_order_id` / `outbound_order_id`. Trong hệ thống mới, lịch sử di chuyển đã có sẵn trong `TransportRequest` + `FleetTask`, và lịch sử gia công nằm trong `ProductionRecord`.

---

### 2.5. Module `stocktake/` ([`backend/legacy_wms_archive/stocktake/`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/stocktake)) & `unit/` ([`backend/legacy_wms_archive/unit/`](file:///D:/Cty_sptech/kuka/backend/legacy_wms_archive/unit))

- **`stocktake_service.py`**:
  - `create_stocktake`: Chụp số lượng lý thuyết (`desired_quantity`) của các `ItemStock` vào bảng `stocktake_item`.
  - `record_stocktake_item_count`: Công nhân nhập số lượng kiểm đếm thực tế (`actual_quantity`).
  - `confirm_quantity_for_stock`: Admin duyệt và ghi đè `item_stock.quantity = row.actual_quantity`.
- **`unit_service.py`**:
  - Quản lý danh mục đơn vị (`Unit`), hệ số quy đổi (`ItemUnit`), và hàm `convert_quantity()` đổi từ Thùng/Pallet ra đơn vị cơ sở.

---

## 3. BẢNG ĐỐI CHIẾU: CƠ CHẾ LOCK & VẬN CHUYỂN CŨ vs. MỚI

Để bạn dễ dàng so sánh và quyết định khi chỉnh sửa code sau này:

| Khía cạnh kỹ thuật | Bản Cũ (`legacy_wms_archive`) | Bản Mới (`app/modules/production` + `location_map`) | Đánh giá & Việc cần làm tiếp |
| :--- | :--- | :--- | :--- |
| **Đơn vị chuyên chở** | `ItemStock` (Pallet) + `QR_Code` rời | `ItemStock` (WIP Cart có `cart_code` cố định) | Bản mới gọn hơn, không cần bảng `qr_code`. |
| **Khóa vị trí đích (Target Lock)** | Lưu tạm trên Redis `inbound:reserved:{loc_id}` lúc gợi ý; xóa ngay khi tạo đơn. | Lưu trực tiếp trong DB: `ItemStock.destination_location_id = target_id` + `is_locked = True` $\rightarrow$ `Location.status` tự động thành **`"reserved"`**. | **Bản mới an toàn và bền vững hơn nhiều** (không sợ mất khóa khi Redis flush hoặc lệch giữa Redis và DB). |
| **Khóa xe/hàng ở vị trí nguồn (Source Lock)** | Dùng subquery `available_quantity` trừ đi `OutboundOrderAllocation` hoặc đặt `status = "in_transit"`. | Đặt trực tiếp trên dòng `ItemStock`: `is_locked = True`, `locked_by_task_id = req_code`, `status = "locked"`. | Bản mới nhanh hơn (không tốn subquery `SUM()` trên mọi câu query `ItemStock`). Cần thêm `.with_for_update()` khi tìm xe để chống 2 người bấm cùng lúc. |
| **Gửi lệnh xuống Robot RCS** | `TaskStatusService.create_robot_task` gửi HTTP POST `:7000/ics/taskOrder/addTask` với `taskPath: "start,target"`. | Mới tạo dòng `FleetTask(status="sent")` trong DB, chưa gọi HTTP POST thật. | **Cần rút hàm `add_task` từ `robot_service.py` cũ sang gắn vào `DispatchService` mới.** |
| **Nhận Callback từ Robot & Đổi vị trí kho** | `TaskStatusService.receive_task_status` (qua Celery `robot.persist_task_status`) bắt buộc kiểm tra `inbound_order_detail` / `outbound_order_allocation` rồi mới gán `stock.location_id = to_location_id`. | Có hàm `DispatchService.simulate_fleet_arrival` đổi `cart.location_id = dropoff_location_id` và mở khóa `is_locked = False` (không cần Inbound/Outbound). | **Cần nối Webhook API + Celery retry của `robot` cũ vào hàm `complete_fleet_task` / `fail_fleet_task` của `DispatchService` mới.** |
| **Xử lý khi trạm đích bận / chưa có xe** | Báo lỗi văng ra ngay, công nhân phải tự canh và bấm lại. | Tự động xếp vào `TransportQueue` (`WAITING_CART` / `WAITING_WASH_SLOT`) và tự động bắn lệnh ngay khi có xe hoặc trống ô rửa. | Bản mới vượt trội hoàn toàn. |
| **Lệnh di chuyển tự do (Point-to-Point Move từ A $\rightarrow$ B)** | Phải tạo giả 1 đơn Inbound hoặc Outbound rất rườm rà. | Có thể viết thêm 1 hàm `move_cart_point_to_point(db, cart_id, target_location_id)` chỉ 30 dòng trong `DispatchService` dùng chung cơ chế Lock hiện tại! | Rất dễ bổ sung ngay trong `DispatchService`. |
