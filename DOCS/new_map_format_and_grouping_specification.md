# ĐẶC TẢ KỸ THUẬT: ĐỊNH DẠNG BẢN ĐỒ MỚI KUKA V2, GOM NHÓM CÔNG ĐOẠN CNC & ĐIỀU PHỐI FIFO LEVEL 0

> **Dự án**: KUKA AMR CNC Machining & WMS System  
> **Tài liệu**: Technical Specification & Architecture Report  
> **Tệp bản đồ nghiên cứu**: `map_CNC001_CNC001_28s.json`  
> **Mã Migration Alembic**: `20261016_1600_d6e7f8a9b0c1_add_default_stage_level_to_location.py`  
> **Trạng thái**: Đã triển khai và vượt qua toàn bộ Test Suites  

---

## 1. TỔNG QUAN & BỐI CẢNH (OVERVIEW & OBJECTIVES)

Hệ thống điều phối xe phôi tự động (KUKA AMR CNC Pipeline) yêu cầu chuyển đổi từ định dạng bản đồ topo nén cũ (`compress.json`) sang định dạng bản đồ sàn chuẩn KUKA AMR thế hệ mới (`map_CNC001_CNC001_28s.json`), đồng thời hiện thực hóa hai quy chuẩn quan trọng từ phân tích vận hành thực tế:
1. **Quản đốc linh hoạt gom nhóm công đoạn CNC**: Cho phép Quản đốc phân công máy/vị trí này gia công công đoạn Level mấy (Level 1, Level 2, Level 3...) thông qua trường cấu hình `default_stage_level` trên bảng `location`.
2. **Quy tắc điều phối phôi thô Level 0 (FIFO)**: Khi các máy Level 1 gọi phôi thô từ Khu Nguyên Liệu, bắt buộc phải tuân theo nguyên tắc **FIFO (First-In, First-Out)** dựa theo thời gian nạp xe (`created_at ASC`) để đảo bảo không tồn phôi cũ. Ngược lại, việc trung chuyển phôi bán thành phẩm giữa các máy CNC (Level > 1) tiếp tục áp dụng **Euclidean 2D Distance** gần nhất để tối ưu thời gian di chuyển của AMR.

---

## 2. PHÂN TÍCH SO SÁNH ĐỊNH DẠNG BẢN ĐỒ (LEGACY VS. KUKA V2)

### 2.1. Cấu trúc bản đồ cũ (`compress/compress.json`)
* **Đơn vị tọa độ**: Milimét (mm), ví dụ: `x = 25208`, `y = 15823`.
* **Cấu trúc trường**:
  * `width`, `height`: Kích thước bounding box (mm).
  * `nodeKeys`: `['x', 'y', 'type', 'content', 'name', 'isTurn', 'shelfIsTurn', 'extraTypes']`.
  * `lineKeys`: `['from', 'to', 'leftWidth', 'rightWidth', 'startExpandDistance', 'endExpandDistance', 'path']`.
  * `nodeArr`: Mảng 2 chiều, trong đó node kệ có `type = 1` và tên tuân theo regex `R{row}_C{col}_L{level}_B{bin}`.
  * `lineArr`: Mảng chứa tọa độ đoạn thẳng `path: [[x1, y1], [x2, y2]]`.

### 2.2. Cấu trúc bản đồ mới KUKA V2 (`map_CNC001_CNC001_28s.json`)
* **Đơn vị tọa độ**: Mét (m), ví dụ: `xCoordinate = 174.315`, `yCoordinate = 77.367`.
* **Cấu trúc gốc**:
  ```json
  {
    "floorList": [
      {
        "floorLevel": 1,
        "floorName": "CNC001",
        "floorNumber": "CNC001",
        "floorLength": 199.5,
        "floorWidth": 95.7,
        "floorMapVersion": "1.0.0",
        "laserMapId": -1,
        "nodeList": [ ... 493 nodes ... ],
        "edgeList": [ ... 704 edges ... ]
      }
    ],
    "mapCode": "CNC001"
  }
  ```
* **Chi tiết `nodeList` (493 nodes)**:
  * `nodeNumber`: Số thứ tự nút (duy nhất, từ 1 đến 514).
  * `nodeLabel`: Nhãn định danh (chuỗi, ví dụ: `"1"`, `"2"`, `"507"`).
  * `nodeUuid`: Định danh duy nhất toàn cục (`"CNC001-CNC001-1"`).
  * `xCoordinate`, `yCoordinate`: Tọa độ thực tế theo mét.
  * `functionList`: Mảng chứa các thuộc tính chức năng. 470 nodes rỗng là các waypoint di chuyển thuần túy; **23 nodes có `functionList`** là các điểm chức năng:
    * `functionType = 4` (2 nodes: #2, #189): **Trạm máy / Thiết bị ngoại tuyến** (`deviceId`: `"offline_device-CNC001-CNC001-2"`). Vị trí đặt máy CNC.
    * `functionType = 10` (2 nodes: #1, #188): **Điểm Docking / Tiếp cận trạm** (`relativeNodeLabel`: `"2"`, `"189"`). Nút AMR dừng trước khi ghép vào máy.
    * `functionType = 2` (16 nodes: #4, #17, #18, #20, #23, #24, #25, #26, #50, #51, #127, #128, #129, #130, #216, #249): **Kệ lưu trữ / Slot xe phôi** (`containerModel`: `"1001"`, `"Rack_Long"`).
    * `functionType = 3` (3 nodes: #40, #41, #42): **Trạm sạc / Chờ tự động** (Charging Stations).
* **Chi tiết `edgeList` (704 edges)**:
  * `beginNodeLabel`, `endNodeLabel`: Nút bắt đầu và nút kết thúc của cung điều hướng.
  * `edgeLength`: Chiều dài đoạn đường (m).
  * `maxVelocity`: Vận tốc tối đa cho phép của AMR (m/s).
  * `edgeType`, `edgeWeight`, `direction`: Thông số dẫn hướng AMR.

---

## 3. THIẾT KẾ & NÂNG CẤP DATABASE

### 3.1. Bổ sung trường `default_stage_level` vào `Location`
Quản đốc sản xuất cần có khả năng quy định trước từng máy hoặc vị trí trên layout bản đồ thuộc công đoạn gia công Level mấy.
* Cột: `default_stage_level INT NULL`
* Index: `ix_location_default_stage_level`
* Ý nghĩa:
  * `NULL`: Vị trí chung hoặc khu đệm/rửa/sạc.
  * `1`: Vị trí thuộc Công đoạn CNC Level 1 (yêu cầu phôi thô Level 0).
  * `2`: Vị trí thuộc Công đoạn CNC Level 2 (yêu cầu phôi Level 1).
  * `3`: Vị trí thuộc Công đoạn CNC Level 3 (yêu cầu phôi Level 2, hoàn tất chuyển đi rửa).

### 3.2. Migration Alembic
Tệp migration: `backend/alembic/versions/20261016_1600_d6e7f8a9b0c1_add_default_stage_level_to_location.py`:
```python
def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    loc_cols = {col["name"] for col in insp.get_columns("location")}
    if "default_stage_level" not in loc_cols:
        op.add_column(
            "location",
            sa.Column("default_stage_level", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_location_default_stage_level"),
            "location",
            ["default_stage_level"],
            unique=False,
        )
```

---

## 4. BỘ CHUYỂN ĐỔI BẢN ĐỒ (MAP ADAPTER & PARSER ENGINE)

Để đảm bảo Frontend Canvas 2D (`WarehouseMapCanvas.tsx`) tiếp tục hoạt động mượt mà mà không phải viết lại toàn bộ canvas engine, backend đã thiết kế kiến trúc **Dual-Compatibility**:

```
[File Upload: .zip / .json]
         │
         ▼
[_read_map_raw_content]  ─── Tự động nhận diện định dạng
         │
    ┌────┴──────────────────────────┐
    ▼                               ▼
[KUKA V2 Floor Format]     [Legacy Compress Format]
    │                               │
    ├─> Mét -> Milimét (* 1000)     └─> Trả về nguyên bản
    ├─> Trích xuất 23 Func Nodes
    ├─> Nối Edges thành path 2D
    ▼                               ▼
[MapDataResponse chuẩn hóa trả về Frontend Canvas & API Sync Location]
```

### 4.1. Quy tắc chuyển đổi tọa độ
* `map_x = round(xCoordinate * 1000)` (mm)
* `map_y = round(yCoordinate * 1000)` (mm)
* `width = round(floorLength * 1000)` = $199.5 \times 1000 = 199,500\text{ mm}$
* `height = round(floorWidth * 1000)` = $95.7 \times 1000 = 95,700\text{ mm}$

### 4.2. Khớp nối tự động Edge thành đường vẽ Canvas
Mỗi `edge` trong `edgeList` được map với tọa độ 2 nút đầu mút để tạo thành `path: [[x1, y1], [x2, y2]]` trong `lineArr`:
```python
for e in edges:
    p1 = node_coords.get(str(e.get("beginNodeLabel")))
    p2 = node_coords.get(str(e.get("endNodeLabel")))
    if p1 and p2:
        line_arr.append([b_lbl, e_lbl, 600, 600, 1200, 1200, [[p1[0], p1[1]], [p2[0], p2[1]]]])
```

### 4.3. Đồng bộ 23 điểm chức năng vào cơ sở dữ liệu `Location`
Khi import map mới:
* 470 nút định hướng đóng vai trò là mạng lưới di chuyển cho xe và vẽ đường đi trên Canvas.
* 23 nút có `functionList` được tự động chuyển đổi thành các thực thể `Location`:
  * `functionType = 4`: `location_type = 'CNC_SLOT'`, `machine_code = 'CNC001'`, `position_index = 1`.
  * `functionType = 10`: `location_type = 'CNC_SLOT'`, `bin_code = 'DOCK_{lbl}'`, `position_index = 2`.
  * `functionType = 2`: `location_type = 'RAW_MATERIAL'`, `bin_code = 'RACK_{lbl}'`.
  * `functionType = 3`: `location_type = 'CHARGING_SLOT'`, `bin_code = 'CHG_{lbl}'`.

---

## 5. THUẬT TOÁN ĐIỀU PHỐI (FIFO LEVEL 0 VS. EUCLIDEAN DISTANCE LEVEL > 0)

Trong `backend/app/modules/production/dispatch_service.py`:

```python
@classmethod
def find_nearest_available_cart(
    cls,
    db: Session,
    target_location: Location,
    item_id: int,
    required_stage_level: int,
) -> Optional[ItemStock]:
    candidate_query = (
        db.query(ItemStock)
        .filter(
            ItemStock.item_id == item_id,
            ItemStock.current_stage_level == required_stage_level,
            ItemStock.is_locked.is_(False),
            ItemStock.is_active.is_(True),
            ItemStock.location_id.isnot(None),
            ItemStock.location_id != target_location.id,
        )
    )

    if required_stage_level == 0:
        # 1. FIFO cho Level 0: Ưu tiên xe nạp vào sàn sớm nhất
        return candidate_query.order_by(ItemStock.created_at.asc(), ItemStock.id.asc()).first()

    # 2. Euclidean 2D Distance cho Level > 0 (trung chuyển giữa các máy CNC)
    candidate_carts = candidate_query.all()
    if not candidate_carts:
        return None

    scored_carts = []
    for cart in candidate_carts:
        if cart.location:
            dist = cls.calculate_distance(cart.location, target_location)
            scored_carts.append((dist, cart))

    if not scored_carts:
        return None

    scored_carts.sort(key=lambda x: x[0])
    return scored_carts[0][1]
```

### Ưu tiên nhận diện Công đoạn Máy (`get_stage_info_for_machine`):
1. **Ưu tiên 1**: `default_stage_level` được Quản đốc thiết lập trực tiếp trên `Location`.
2. **Ưu tiên 2**: Cấu hình `ProductionRoute` & `RouteStep` theo mã máy `machine_code`.
3. **Ưu tiên 3**: Fallback theo quy ước tên máy (`CNC-01/02` -> Level 1, `CNC-03` -> Level 2, `CNC-04` -> Level 3).

---

## 6. KẾT QUẢ KIỂM THỬ & XÁC MINH (VERIFICATION)

Hai bộ kịch bản kiểm thử độc lập đã được thực thi trên môi trường thực tế:

1. **`test_dispatch_engine.py`**:
   * TEST 1: Nearest Cart Selection via 2D Euclidean Distance -> **PASSED**
   * TEST 2: Request Material to Empty CNC Position (CNC01_POS1) -> **PASSED**
   * TEST 3: Simulate AMR Arrival at CNC01_POS1 -> **PASSED**
   * TEST 4: Double-Buffering / Pos 2 Calling (Zero CNC Starvation) -> **PASSED**
   * TEST 5: Report Stage 1 Completed at CNC01_POS1 -> **PASSED**
   * TEST 6: Final Stage Completion (CNC-04) & Wash Transfer -> **PASSED**
   * TEST 7: Release Wash Slot & Return Empty Cart -> **PASSED**
   * **Kết quả**: 7/7 core dispatch tests passed.

2. **`test_new_map_and_fifo.py`**:
   * **Supervisor default_stage_level**: Cập nhật và lưu trữ thành công trên DB -> **PASSED**
   * **Level 0 FIFO Verification**: Xe `TEST-FIFO-OLD` (nạp trước) được chọn ưu tiên tuyệt đối so với xe `TEST-FIFO-NEW` dù ở xa hơn -> **PASSED**
   * **Level 2 Euclidean Distance Verification**: Xe `TEST-FIFO-NEW` (khoảng cách 2236.1mm) được chọn so với `TEST-FIFO-OLD` (khoảng cách 2267.2mm) -> **PASSED**
   * **KUKA Floor Map Parser**: Tự động nhận diện `map_CNC001_CNC001_28s.json`, trích xuất đúng 23 shelf nodes, chuyển đổi 493 canvas nodes và 704 canvas edges ở tỉ lệ milimét chuẩn -> **PASSED**
