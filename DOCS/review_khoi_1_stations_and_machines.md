# TÀI LIỆU TOÀN DIỆN REVIEW KHỐI 1: TRẠM MÁY CNC & PHÂN KHU XƯỞNG
*(STATIONS & PHYSICAL SHOP LAYOUT SPECIFICATION & TRACEABILITY)*

Tài liệu này đặc tả chi tiết toàn bộ các file tham gia, cấu trúc dữ liệu, các luồng tương tác trọn vẹn CRUD (Create, Read, Update, Delete) từ **Giao diện Component (Frontend) $\rightarrow$ Hook / Client API $\rightarrow$ REST API Endpoint & Schemas $\rightarrow$ Service Logic $\rightarrow$ Bảng Cơ sở dữ liệu (PostgreSQL)** của **Khối 1: Trạm Máy & Phân Khu Xưởng**.

---

## 🗺️ 1. SƠ ĐỒ LUỒNG ĐI TỔNG THỂ (FULL-STACK FLOW)

```mermaid
sequenceDiagram
    autonumber
    actor User as Quản Đốc Xưởng
    participant UI as StationSettingPage.tsx
    participant Hook as useStations.ts / useMachines.ts
    participant API as api/station.ts / api/machine.ts
    participant Router as station_api.py / machine_api.py
    participant Schema as station_schema.py / machine_schema.py
    participant Service as station_service.py / machine_service.py
    participant DB as PostgreSQL (machine, location, item_stock)

    Note over User,DB: LUỒNG TẢI DỮ LIỆU HIỆN TRẠNG (READ CATALOG & AVAILABLE NODES)
    User->>UI: Mở trang Cấu hình Trạm (/production/stations)
    UI->>Hook: useStationCatalog() & useAvailableNodes()
    Hook->>API: getStationCatalogApi() & getAvailableMapNodesApi()
    API->>Router: GET /api/v1/production/stations/catalog & /map/available-nodes
    Router->>Service: station_service.get_station_catalog(db)
    Service->>DB: Query bảng machine (3NF) & location (RAW, CNC, WASH, EMPTY BUFFER)
    DB-->>Service: Dữ liệu thực thể
    Service->>Schema: Validate & đóng gói StationCatalogResponse
    Schema-->>Router-->>API-->>Hook-->>UI: Catalog & Map Nodes
    UI-->>User: Hiển thị 4 Tab chuyên biệt (Cấp Phôi | Máy CNC | Khu Tẩy Rửa | Bãi Đệm Xe Rỗng)

    Note over User,DB: LUỒNG CẬP NHẬT / XÓA MÁY HOẶC TRẠM (UPDATE / DELETE)
    User->>UI: Bấm Chỉnh sửa hoặc Xóa máy / trạm
    UI->>Hook: useUpdateMachine / useDeleteMachine (hoặc StationLocation)
    Hook->>API: updateMachineApi / deleteMachineApi
    API->>Router: PUT/DELETE /api/v1/production/machines/{id} hoặc /stations/locations/{id}
    Router->>Service: Kiểm tra ràng buộc phôi tồn (item_stock), đồng bộ node map
    Service->>DB: UPDATE hoặc chuyển location_type = 'UNASSIGNED'
    DB-->>Service: Giao dịch thành công (Commit)
    Service-->>Router-->>API-->>Hook-->>UI: HTTP 200 OK / HTTP 204 No Content
    Hook->>Hook: invalidateQueries(['stationCatalog', 'machines', 'availableMapNodes'])
    UI-->>User: Refresh tự động toàn bộ 4 Tab và Node Map
```

---

## 📂 2. TỔNG HỢP CÁC FILE THAM GIA TRONG KHỐI 1 (INVOLVED FILES)

| Tầng | Đường Dẫn File | Vai Trò & Trách Nhiệm |
| :--- | :--- | :--- |
| **Frontend UI** | [frontend/src/pages/production/StationSettingPage.tsx](file:///D:/KuKA/KUKA_WMS/frontend/src/pages/production/StationSettingPage.tsx) | Trang quản trị chính 4 Tab: Cấp phôi, Máy CNC (1..3 slot POS), Khu tẩy rửa, Bãi đệm xe rỗng. |
| **Frontend UI** | [frontend/src/pages/components/StationAssignmentModal.tsx](file:///D:/KuKA/KUKA_WMS/frontend/src/pages/components/StationAssignmentModal.tsx) | Modal phân quyền vị trí thao tác cho công nhân theo tài khoản (1 user = 1 area duy nhất). |
| **Frontend UI** | [frontend/src/routes/index.tsx](file:///D:/KuKA/KUKA_WMS/frontend/src/routes/index.tsx) | Đăng ký route `/production/stations`, redirect `/machines` và `/zones` sang `/production/stations`. |
| **Frontend UI** | [frontend/src/components/layout/Sidebar.tsx](file:///D:/KuKA/KUKA_WMS/frontend/src/components/layout/Sidebar.tsx) | Menu điều hướng sidebar: "Cấu hình Trạm". |
| **Frontend Hooks** | [frontend/src/hooks/useStations.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/hooks/useStations.ts) | React Query hooks Trạm: `useStationCatalog`, `useAvailableNodes`, `useCreateStationLocation`, `useUpdateStationLocation`, `useDeleteStationLocation`. |
| **Frontend Hooks** | [frontend/src/hooks/useMachines.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/hooks/useMachines.ts) | React Query hooks Máy CNC: `useMachines`, `useCreateMachine`, `useUpdateMachine`, `useDeleteMachine`, `useUserLocations`, `useUpdateUserLocations`. |
| **Frontend API Client** | [frontend/src/api/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/station.ts) | Axios client chuyên trách Trạm: Catalog, Node bản đồ, CRUD vị trí độc lập (`RAW_MATERIAL`, `WASHING_SLOT`, `EMPTY_CART_BUFFER`). |
| **Frontend API Client** | [frontend/src/api/machine.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/machine.ts) | Axios client chuyên trách Máy CNC: CRUD máy CNC, cấu hình 1..3 slot đỗ và phân quyền vị trí cho user. |
| **Frontend Types** | [frontend/src/types/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/types/station.ts) | Interface TypeScript Trạm: `StationCatalogResponse`, `StationCatalogItem`, `AvailableMapNode`, `StationLocationCreateInput`, `StationLocationUpdateInput`. |
| **Frontend Types** | [frontend/src/types/machine.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/types/machine.ts) | Interface TypeScript Máy CNC: `MachineItem`, `MachineSlotInfo`, `MachineCreateInput`, `MachineUpdateInput`, `SlotConfigInput`. |
| **Backend Router** | [backend/app/modules/production/station_api.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_api.py) | Router chuyên trách Trạm (`@station_router`): Catalog, Node bản đồ, CRUD vị trí độc lập. |
| **Backend Router** | [backend/app/modules/production/machine_api.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/machine_api.py) | Router chuyên trách Máy CNC (`@machine_router`): CRUD máy CNC và quản lý 1..3 slot POS. |
| **Backend Router** | [backend/app/modules/production/route_api.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/route_api.py) | Root router mount `station_router`, `machine_router` và chứa endpoint gán quyền vị trí user. |
| **Backend Schemas** | [backend/app/modules/production/station_schema.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_schema.py) | Pydantic Models Trạm: `StationCatalogResponse`, `StationCatalogItem`, `StationSlotCreateRequest`, `StationSlotUpdateRequest`, `MapAvailableNodeResponse`. |
| **Backend Schemas** | [backend/app/modules/production/machine_schema.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/machine_schema.py) | Pydantic Models Máy CNC: `AvailableMachineResponse`, `MachineSlotInfo`, `MachineCreateRequest`, `MachineUpdateRequest`, `MachineSlotCreate`. |
| **Backend Service** | [backend/app/modules/production/station_service.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_service.py) | Service Trạm: Truy vấn catalog 4 khu vực, đọc map nodes, tạo/sửa/xóa ô cấp phôi, trạm rửa, bãi đệm xe rỗng. |
| **Backend Service** | [backend/app/modules/production/machine_service.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/machine_service.py) | Service Máy CNC: Tạo máy, cấp phát động 1..3 slot POS, sửa máy/slot, xóa máy an toàn với kiểm tra phôi tồn. |
| **Database Models** | [backend/app/modules/production/production_models.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/production_models.py) | Model thực thể `Machine` (3NF), `UserLocation`. |
| **Database Models** | [backend/app/modules/warehouse/location_map/location_model.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/warehouse/location_map/location_model.py) | Model thực thể `Location` (Vị trí đỗ vật lý của AMR trên toàn phân xưởng). |
| **Dữ Liệu Bản Đồ Gốc** | [map_CNC001_CNC001_28s.json](file:///D:/KuKA/KUKA_WMS/map_CNC001_CNC001_28s.json) | Bản đồ xưởng KUKA gốc (493 nodes, trích xuất 23 functional rack nodes). |

---

## 🔍 3. CHI TIẾT CÁC LUỒNG THAO TÁC CỤ THỂ

### 🟢 LUỒNG 1: TẢI DANH MỤC TRẠM XƯỞNG HỢP NHẤT (READ STATION CATALOG)
Mục đích: Lấy toàn bộ hiện trạng trạm xưởng để hiển thị lên 4 Tab chuyên biệt của màn hình quản trị.

1. **Giao diện (Component)**:
   - `StationSettingPage.tsx`: Gọi `const { data: catalog, isLoading, refetch } = useStationCatalog();`.
   - Render 4 Tab chuyên biệt:
     * **Tab 1: `raw_material`** $\rightarrow$ Bảng danh sách các ô cấp phôi (`catalog.raw_materials`).
     * **Tab 2: `cnc`** $\rightarrow$ Thẻ quản lý các máy CNC (`catalog.machines`), mỗi máy hiển thị badge các vị trí đỗ `POS1`, `POS2`, `POS3` kèm tọa độ map.
     * **Tab 3: `washing`** $\rightarrow$ Bảng danh sách các trạm rửa phôi (`catalog.washing_slots`).
     * **Tab 4: `empty_buffer`** $\rightarrow$ Bảng danh sách các bãi đệm xe rỗng (`catalog.empty_buffers`).
2. **Hook & Client API**:
   - `useStationCatalog()` trong [useStations.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/hooks/useStations.ts) $\rightarrow$ gọi `getStationCatalogApi()`.
   - `getStationCatalogApi()` trong [api/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/station.ts) $\rightarrow$ Gửi request:
     ```http
     GET /api/v1/production/stations/catalog
     ```
3. **Backend API Route**:
   - Endpoint: `@station_router.get("/production/stations/catalog", response_model=StationCatalogResponse)` trong [station_api.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_api.py).
4. **Backend Service**:
   - Hàm `station_service.get_station_catalog(db)` trong [station_service.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_service.py):
     * Query bảng `Machine` sắp xếp theo `machine_code ASC`.
     * Với mỗi máy, lấy danh sách `Location` con có `machine_id == m.id` và `is_active == True`, xếp theo `position_index ASC`.
     * Query bảng `Location` lấy các vị trí độc lập:
       - `Location.location_type == 'RAW_MATERIAL'` $\rightarrow$ gom vào `raw_materials`.
       - `Location.location_type == 'WASHING_SLOT'` $\rightarrow$ gom vào `washing_slots`.
       - `Location.location_type == 'EMPTY_CART_BUFFER'` $\rightarrow$ gom vào `empty_buffers` (đã bỏ hẳn `buffer_slots` dư thừa).
5. **Schema Trả Về**:
   - `StationCatalogResponse` trong [station_schema.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_schema.py):
     ```python
     class StationCatalogResponse(BaseModel):
         raw_materials: list[StationCatalogItem]  # Các ô cấp phôi VT-01..07
         machines: list[MachineCatalogGroup]       # Danh sách máy CNC, mỗi máy chứa 1..3 slot POS
         washing_slots: list[StationCatalogItem]  # Slot tẩy rửa WASH-01..04
         empty_buffers: list[StationCatalogItem]  # Bãi đệm xe rỗng EMPTY-01..04
     ```

---

### 🔵 LUỒNG 2: LẤY DANH SÁCH NODE BẢN ĐỒ KHẢ DỤNG (AVAILABLE MAP NODES)
Mục đích: Cung cấp danh sách các Node điểm đỗ có sẵn từ Map xưởng để khi Quản đốc tạo/sửa máy CNC hoặc ô phôi có thể chọn gắn ngay, không phải nhập tọa độ thủ công.

1. **Giao diện (Component)**:
   - Dropdown Select "Chọn Node Bản Đồ (KUKA Map)" trong Modal Thêm/Sửa trạm của `StationSettingPage.tsx`.
   - Option hiển thị nhãn: `Node [node_label] (x: ..., y: ...) - [Chưa gán / Đã gán cho ...]`.
2. **Hook & Client API**:
   - `useAvailableNodes()` trong [useStations.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/hooks/useStations.ts) $\rightarrow$ gọi `getAvailableMapNodesApi()` trong [api/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/station.ts).
   - Endpoint: `GET /api/v1/production/map/available-nodes`.
3. **Backend Service**:
   - Hàm `station_service.get_available_map_nodes(db)` trong [station_service.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_service.py):
     * Đọc các bản ghi `Location` có `is_active == True` và `function_type == 2` (Rack node).
     * Node được coi là đã gán nếu `location_type != 'UNASSIGNED'`. Gán `is_assigned = True` và ghi rõ `assigned_to` (VD: "CNC_SLOT: CNC-01 (POS1)" hoặc "RAW_MATERIAL: Ô Cấp Phôi VT-01").
4. **Schema Trả Về**:
   - `MapAvailableNodeResponse` trong [station_schema.py](file:///D:/KuKA/KUKA_WMS/backend/app/modules/production/station_schema.py):
     ```python
     class MapAvailableNodeResponse(BaseModel):
         node_number: int          # Số thứ tự node (VD: 216)
         node_label: str           # Nhãn node (VD: "216")
         map_x: int                # Tọa độ X bản đồ (mm)
         map_y: int                # Tọa độ Y bản đồ (mm)
         function_type: int        # Loại node (2 = Rack station)
         is_assigned: bool         # True nếu đã gán cho trạm nào đó
         assigned_to: str | None   # Tên trạm đang chiếm giữ node
     ```

---

### 🟡 LUỒNG 3: QUẢN LÝ MÁY CNC & VỊ TRÍ ĐỖ (CREATE, UPDATE, DELETE MÁY CNC)

#### 3.1. Tạo Máy CNC Mới (`CREATE`)
1. **Giao diện**: Nút **[+ Thêm Máy CNC]** trên Tab 2 mở modal `isCncCreateOpen`. Quản đốc nhập Mã máy (VD: `CNC-05`), Tên máy, và thiết lập động 1..3 vị trí đỗ (`POS1`, `POS2`, `POS3`) gắn với các node map.
2. **Client API & Endpoint**:
   - Hook: `useCreateMachine()` gọi `createMachineApi(payload)` trong [api/machine.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/machine.ts).
   - Request:
     ```http
     POST /api/v1/production/machines
     Content-Type: application/json

     {
       "machine_code": "CNC-05",
       "machine_name": "Máy Phay CNC 05",
       "slots": [
         { "position_index": 1, "node_label": "216", "map_x": 164249, "map_y": 52600 },
         { "position_index": 2, "node_label": "249", "map_x": 156049, "map_y": 52600 }
       ]
     }
     ```
3. **Backend Service (`machine_service.create_machine`)**:
   - Kiểm tra trùng `machine_code` $\rightarrow$ ném lỗi nếu đã có.
   - Thêm bản ghi vào bảng `machine` (3NF).
   - Duyệt từng slot trong mảng `slots`: Tìm hoặc cập nhật `Location` tương ứng, đặt `location_type = 'CNC_SLOT'`, `machine_id = machine.id`, `position_index = pos`, cập nhật tọa độ map.
   - Trả về `AvailableMachineResponse`.

#### 3.2. Cập Nhật Máy CNC & Đồng Bộ Slots (`UPDATE`)
1. **Giao diện**: Nút **[Chỉnh Sửa]** (icon Edit) trên Card từng máy mở modal `editingCnc`. Cho phép:
   - Đổi tên máy (`machine_name`).
   - Thêm vị trí đỗ thứ 3 (nếu đang có 2 slot) hoặc xóa bớt vị trí đỗ về 1 slot.
   - Đổi Node Map liên kết cho từng vị trí đỗ `POS1`, `POS2`, `POS3`.
2. **Client API & Endpoint**:
   - Hook: `useUpdateMachine()` gọi `updateMachineApi(id, payload)` trong [api/machine.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/machine.ts).
   - Request:
     ```http
     PUT /api/v1/production/machines/{machine_id}
     Content-Type: application/json

     {
       "machine_name": "Máy Phay CNC 05 (Đã Nâng Cấp)",
       "slots": [
         { "id": 189, "position_index": 1, "node_label": "216", "map_x": 164249, "map_y": 52600 },
         { "id": 190, "position_index": 2, "node_label": "250", "map_x": 156049, "map_y": 52600 },
         { "position_index": 3, "node_label": "251", "map_x": 148000, "map_y": 52600 }
       ]
     }
     ```
3. **Backend Service (`machine_service.update_machine`)**:
   - Cập nhật thông tin `m.machine_name`.
   - **Kiểm tra an toàn tồn kho (Guard Clause khi Update)**:
     * **Khi giảm bớt slot** (ví dụ máy giảm từ 3 slot xuống 2 slot): Duyệt các slot bị loại bỏ (`to_remove`), kiểm tra trong bảng `ItemStock`. Nếu slot đang có hàng tồn (`ItemStock.quantity > 0` và `is_active == True`), ném lỗi `ValueError("Không thể giảm bớt vị trí đỗ ... vì đang có phôi hoặc xe đỗ.")`.
     * **Khi đổi Node map của slot**: Nếu slot hiện tại đang chứa phôi chờ gia công/chờ AGV, hoặc Node mới đang có hàng tồn của khu khác $\rightarrow$ ném lỗi từ chối đổi điểm.
   - **Xử lý slot bị bớt an toàn**: Với các slot thỏa mãn không có hàng tồn, tự động giải phóng vị trí về trạng thái tự do:
     * `loc.machine_id = None`
     * `loc.position_index = None`
     * `loc.location_type = 'UNASSIGNED'`
     * `loc.location_name = loc.location_label or str(loc.id)`
   - Cập nhật thông tin tọa độ map, nhãn node cho các slot còn lại.
   - Trả về `AvailableMachineResponse` đã cập nhật.

#### 3.3. Xóa / Thu Hồi Máy CNC (`DELETE`)
1. **Giao diện**: Nút **[Xóa]** (icon Thùng rác) hiển thị Popconfirm cảnh báo xác nhận.
2. **Client API & Endpoint**:
   - Hook: `useDeleteMachine()` gọi `deleteMachineApi(id)` trong [api/machine.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/machine.ts).
   - Request:
     ```http
     DELETE /api/v1/production/machines/{machine_id}
     ```
     Response: `204 No Content`.
3. **Backend Service (`machine_service.delete_machine`)**:
   - **Kiểm tra an toàn (Guard Clause)**: Kiểm tra bảng `ItemStock` xem tại bất kỳ vị trí slot con nào của máy có tồn tại phôi hoặc xe đang đỗ (`ItemStock.is_active == True`):
     ```python
     if active_stocks > 0:
         raise ValueError(f"Không thể xóa máy CNC {m.machine_code} đang có phôi hoặc xe đỗ tại vị trí.")
     ```
   - **Giải phóng toàn bộ Slots**: Đưa tất cả `Location` trực thuộc máy về `location_type = 'UNASSIGNED'`, `machine_id = None`, `position_index = None`.
   - **Dọn dẹp liên kết Route**: Xóa các liên kết công đoạn quy trình trong bảng `route_step_machine`.
   - **Xóa bản ghi Máy**: Gọi `db.delete(m)` và `db.commit()`.

---

### 🟠 LUỒNG 4: QUẢN LÝ CÁC TRẠM ĐỘC LẬP (CẤP PHÔI, TẨY RỬA, BÃI ĐỆM XE RỖNG)

Các trạm độc lập gồm: Ô Cấp Phôi (`RAW_MATERIAL`), Slot Tẩy Rửa (`WASHING_SLOT`) và Bãi Đệm Xe Rỗng (`EMPTY_CART_BUFFER`). Tất cả đều sử dụng chung bộ API quản trị vị trí thống nhất.

#### 4.1. Tạo Vị Trí Trạm Mới (`CREATE`)
1. **Giao diện**:
   - Tab 1: Nút **[+ Thêm Ô Cấp Phôi]** mở modal gán ô nguyên liệu (`RAW_MATERIAL`).
   - Tab 3: Nút **[+ Thêm Slot Tẩy Rửa]** mở modal gán trạm rửa (`WASHING_SLOT`).
   - Tab 4: Nút **[+ Thêm Bãi Đệm]** mở modal gán bãi đệm xe rỗng (`EMPTY_CART_BUFFER`).
2. **Client API & Endpoint**:
   - Hook: `useCreateStationLocation()` gọi `createStationLocationApi(payload)` trong [api/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/station.ts).
   - Request:
     ```http
     POST /api/v1/production/stations/locations
     Content-Type: application/json

     {
       "location_code": "EMPTY-01",
       "location_name": "Bãi Đệm Xe Rỗng 1",
       "location_type": "EMPTY_CART_BUFFER",
       "node_label": "301",
       "map_x": 140000,
       "map_y": 60000,
       "position_index": 1
     }
     ```
3. **Backend Service (`station_service.create_station_slot`)**:
   - Tìm kiếm bản ghi `Location` theo `node_label` hoặc `location_code`.
   - Kiểm tra nếu node đã được gán cho khu vực khác $\rightarrow$ ném lỗi chống trùng lặp.
   - Cập nhật `location_type = loc_type`, gán tên hiển thị, nhãn node và tọa độ bản đồ. Trả về `StationCatalogItem`.

#### 4.2. Cập Nhật Vị Trí Trạm (`UPDATE`)
1. **Giao diện**: Nút **[Chỉnh Sửa]** trên dòng của từng trạm mở modal cập nhật (đổi tên nghiệp vụ hiển thị, đổi vị trí tọa độ, bật/tắt hoạt động).
2. **Client API & Endpoint**:
   - Hook: `useUpdateStationLocation()` gọi `updateStationLocationApi(id, payload)` trong [api/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/station.ts).
   - Request:
     ```http
     PUT /api/v1/production/stations/locations/{location_id}
     Content-Type: application/json

     {
       "location_name": "Bãi Đệm Xe Rỗng Số 1 (Cửa Tây)",
       "node_label": "301",
       "map_x": 140000,
       "map_y": 60000,
       "is_active": true
     }
     ```
3. **Backend Service (`station_service.update_station_slot`)**:
   - Tìm `Location` theo `location_id`.
   - **Kiểm tra an toàn tồn kho (Guard Clause khi Update)**:
     * **Khi đổi Node map sang điểm khác**: Kiểm tra nếu vị trí hiện tại đang có hàng tồn (`ItemStock.quantity > 0`), hoặc Node mới được chọn đang có hàng tồn $\rightarrow$ ném lỗi từ chối di dời vị trí trạm.
     * **Khi vô hiệu hóa (`is_active = false`)**: Nếu vị trí đang có hàng tồn $\rightarrow$ ném lỗi bắt buộc phải giải phóng hàng tồn trước khi tắt trạm.
   - Cập nhật có chọn lọc các trường được gửi lên: `location_name`, `position_index`, `location_label` (từ `node_label`), `map_x`, `map_y`, `is_active`.
   - Lưu DB (`db.commit()`) và trả về `StationCatalogItem` mới nhất.

#### 4.3. Xóa / Giải Phóng Vị Trí Trạm (`DELETE`)
1. **Giao diện**: Nút **[Xóa]** trên từng dòng trạm hiển thị Popconfirm: "Xóa slot / ô / bãi đệm này?".
2. **Client API & Endpoint**:
   - Hook: `useDeleteStationLocation()` gọi `deleteStationLocationApi(id)` trong [api/station.ts](file:///D:/KuKA/KUKA_WMS/frontend/src/api/station.ts).
   - Request:
     ```http
     DELETE /api/v1/production/stations/locations/{location_id}
     ```
     Response: `204 No Content`.
3. **Backend Service (`station_service.delete_station_slot`)**:
   - **Kiểm tra an toàn**: Kiểm tra xem tại vị trí này có tồn tại rack hàng hay phôi đang đỗ hay không (`ItemStock.is_active == True`). Nếu có $\rightarrow$ ném lỗi `ValueError("Không thể giải phóng vị trí... đang có phôi hoặc xe đỗ.")`.
   - **Giải phóng node vật lý (Soft Release)**: Do các vị trí này liên kết với Node trên bản đồ KUKA, hệ thống **không xóa cứng bản ghi `Location`** mà đưa vị trí về trạng thái ban đầu:
     ```python
     loc.location_type = "UNASSIGNED"
     loc.location_name = loc.location_label or str(loc.id)
     loc.machine_id = None
     loc.position_index = None
     loc.is_active = True
     db.commit()
     ```
   - Node sau khi giải phóng sẽ lập tức xuất hiện trở lại trong danh sách Node khả dụng (`availableMapNodes`) để Quản đốc gán cho trạm khác khi cần.

---

## 🗄️ 4. BẢNG ĐỐI CHIẾU CƠ SỞ DỮ LIỆU (DATABASE SCHEMA SPECIFICATION)

### Bảng 1: `machine` (3NF)
| Tên Cột | Kiểu Dữ Liệu | Nullable | Khóa | Mục Đích Nghiệp Vụ |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | PK | Khóa chính máy CNC |
| `machine_code` | `VARCHAR(50)` | `NO` | Unique, Index | Mã máy định danh duy nhất (VD: `CNC-01`, `CNC-02`) |
| `machine_name` | `VARCHAR(100)` | `YES` | | Tên mô tả máy (VD: `Máy Phay CNC 01`) |
| `warehouse_id` | `INTEGER` | `YES` | FK $\rightarrow$ `warehouse.id` | Trực thuộc phân xưởng nào |
| `status` | `VARCHAR(30)` | `NO` | Default: `'available'` | Trạng thái máy (`available`, `busy`, `maintenance`) |
| `is_active` | `BOOLEAN` | `NO` | Default: `True` | Trạng thái hoạt động |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `NO` | Server default `now()` | Thời gian tạo |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `NO` | On update `now()` | Thời gian cập nhật |

### Bảng 2: `location` (Vị trí đỗ vật lý của AMR)
| Tên Cột | Kiểu Dữ Liệu | Nullable | Khóa / Index | Mục Đích Nghiệp Vụ |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | PK | Khóa chính vị trí đỗ |
| `location_code` | `VARCHAR(50)` | `NO` | Unique, Index | Mã vị trí đỗ (VD: `CNC-01-POS1`, `VT-01`, `WASH-01`, `EMPTY-01`) |
| `location_name` | `VARCHAR(100)` | `YES` | | Tên vị trí thân thiện với người dùng |
| `location_label` | `VARCHAR(50)` | `YES` | Index | Nhãn hiển thị trên bản đồ (VD: `216`) |
| `node_label` | `VARCHAR(50)` | `YES` | Index | Mã Node liên kết trong file map KUKA |
| `location_type` | `VARCHAR(30)` | `YES` | Index | Phân loại: `RAW_MATERIAL`, `CNC_SLOT`, `WASHING_SLOT`, `EMPTY_CART_BUFFER`, `UNASSIGNED` |
| `machine_id` | `INTEGER` | `YES` | FK $\rightarrow$ `machine.id` | Liên kết với máy CNC cha (nếu là `CNC_SLOT`) |
| `machine_code` | `VARCHAR(50)` | `YES` | Index | Mã máy cha để truy vấn nhanh |
| `position_index` | `INTEGER` | `YES` | | Vị trí đỗ: `1` (POS1), `2` (POS2), `3` (POS3) |
| `map_x` | `INTEGER` | `YES` | | Tọa độ X bản đồ (đơn vị: mm) |
| `map_y` | `INTEGER` | `YES` | | Tọa độ Y bản đồ (đơn vị: mm) |
| `is_active` | `BOOLEAN` | `NO` | Default: `True` | Bật/tắt vị trí |

> [!IMPORTANT]
> **Cam Kết Vàng Về Kiến Trúc**:
> Cột `default_stage_level` đã bị **XÓA BỎ VĨNH VIỄN** khỏi cả hai bảng `machine` và `location`. Công đoạn Level mấy hoàn toàn do bảng `route_step` trong Quy trình Route quy định.

---

## 🛡️ 5. TIÊU CHÍ KIỂM ĐỊNH CHẤT LƯỢNG KHỐI 1 (QUALITY CHECKLIST)

- [x] **Trọn vẹn chu trình CRUD (Full Lifecycle Support)**:
  - Hỗ trợ đầy đủ Tạo, Đọc, Cập nhật và Xóa/Thu hồi cho cả Máy CNC lẫn các Trạm xưởng độc lập.
  - Có cơ chế chặn xóa an toàn nếu tại vị trí đang có phôi hoặc xe đỗ (`ItemStock`).
- [x] **Ranh giới trách nhiệm (Separation of Concerns)**:
  - Máy CNC (`Machine`) chỉ đóng vai trò phương tiện gia công (Workcenter).
  - Vị trí đỗ (`Location`) đóng vai trò điểm cập bến vật lý của robot AMR.
  - Phân tách rõ ràng giữa 4 phân khu xưởng với 4 Tab độc lập trên giao diện.
- [x] **Tính linh hoạt đệm kép (Buffer Agility)**:
  - Hỗ trợ đầy đủ từ 1 đến 3 vị trí đỗ (POS1, POS2, POS3) trên mỗi máy CNC.
  - Cho phép máy hoạt động theo cơ chế đệm kép liên tục (Zero Starvation) mà không bị giới hạn cứng 2 vị trí như thiết kế cũ.
- [x] **Độ tin cậy bản đồ (Map Ground Truth)**:
  - Tất cả các vị trí đỗ đều liên kết với tọa độ thực tế của Node bản đồ KUKA (`map_CNC001_...json`).
  - Khi xóa/thu hồi trạm, Node tự động giải phóng về trạng thái `UNASSIGNED` để tái sử dụng.
- [x] **An toàn kiểu dữ liệu (Type Safety)**:
  - Đồng bộ 100% giữa TypeScript types (`types/station.ts`, `types/machine.ts`) $\leftrightarrow$ Pydantic Schemas (`station_schema.py`, `machine_schema.py`) $\leftrightarrow$ SQLAlchemy Models.
