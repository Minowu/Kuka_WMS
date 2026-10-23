# KẾ HOẠCH & ĐÁNH GIÁ LUỒNG GIAO DIỆN PDA VẬN HÀNH CNC (`/pda/cnc`)

Tài liệu này chi tiết hóa toàn bộ luồng hoạt động từ **Backend đến Frontend**, cấu trúc dữ liệu, sơ đồ kiến trúc và **hình ảnh minh họa Wireframe giao diện PDA** chuẩn công nghiệp (tỉ lệ 4.2-inch cầm tay) đã được cập nhật chuẩn xác theo thực tế sản xuất tại xưởng.

---

## 1. Cơ chế hoạt động cốt lõi tại trạm CNC

1. **Cơ chế 1-Chạm (Không cần chọn Model):**
   - Công nhân **không cần chọn mã linh kiện/Model**. Khi bấm nút **"GỌI PHÔI (ĐIỀU AMR ĐẾN)"**, Frontend chỉ gửi `destination_location_id`.
   - Backend tự động tra cứu cấu hình máy trong bảng `ProductionRoute` / `RouteStepMachine`:
     - Máy CNC này đang tham gia công đoạn nào? Thuộc Model sản phẩm nào?
     - Cần phôi đầu vào là Level mấy? (Ví dụ: Máy gia công OP2 $\rightarrow$ Tự động tìm phôi Level 1 đang sẵn sàng ở kho hoặc máy trước để điều AMR tới).

2. **Cơ chế Slot Độc lập (POS1 & POS2):**
   - Mỗi máy CNC có 2 vị trí đệm độc lập (POS1 và POS2).
   - **Hạ ở đâu thì lấy đi ở đó:** Khi xe AMR chở phôi tới hạ tại **POS1**, công nhân gia công trực tiếp khay tại POS1. Khi bấm **"Báo xong"**, xe AMR sẽ tới bốc hàng đi từ **chính POS1** (chở sang máy tiếp theo hoặc sang khu rửa `WASH`), hoàn toàn không phải chuyển sang POS2.
   - POS2 đóng vai trò là ô đệm song song thứ 2, giúp máy có thể gối đầu (đang gia công POS1 vẫn có thể gọi thêm phôi về POS2 để máy không bị dừng chờ).

---

## 2. Sơ đồ kiến trúc & Luồng dữ liệu End-to-End

```mermaid
graph TD
    subgraph PDA_Frontend ["PDA Frontend (React 18 + Zustand + Tailwind)"]
        UI["CncPdaPage.tsx (Màn hình 4.2 inch)"]
        Store["usePdaStore.ts (State Manager)"]
        Poller["Polling Loop (Mỗi 60 giây)"]
        LineModal["CncLineModal.tsx (Giao diện thẻ máy)"]
        
        Poller -->|Cập nhật định kỳ| Store
        Store -->|Cung cấp State| UI
        UI --> LineModal
    end

    subgraph Backend_API ["Backend FastAPI Service (app/modules/production)"]
        Router["route_api.py (/api/v1/production/pda)"]
        AuthRBAC["RBAC: _ensure_user_can_access_location"]
        Dispatch["dispatch_service.py (Auto Route & AMR Dispatch)"]
    end

    subgraph Database_PostgreSQL ["PostgreSQL Database"]
        DB_UserLoc[("UserLocation (Gán quyền theo user)")]
        DB_Machine[("Machine & Location (POS1, POS2)")]
        DB_Route[("ProductionRoute (Tự suy Model & Step Level)")]
        DB_Stock[("ItemStock (Khay phôi trên slot)")]
        DB_Task[("FleetTask / TransportRequest (AMR)")]
    end

    Store -->|"1. GET /cnc-stations"| Router
    LineModal -->|"2. POST /call-material (1-chạm)"| Router
    LineModal -->|"3. POST /complete-stage (1-chạm)"| Router

    Router --> AuthRBAC
    AuthRBAC --> DB_UserLoc
    Router --> Dispatch
    Dispatch --> DB_Route
    Dispatch --> DB_Machine
    Dispatch --> DB_Stock
    Dispatch --> DB_Task
```

---

## 3. Sơ đồ trình tự thao tác của Công nhân (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor CNC as Công nhân CNC (PDA)
    participant PDA as Màn hình PDA (CncLineModal)
    participant Store as Store (usePdaStore)
    participant BE as Backend API (route_api)
    participant Dispatch as Dispatch Service (Tự suy Route)
    participant AMR as AMR / Fleet Task

    Note over PDA,Store: Cập nhật dữ liệu mặt bằng (Polling 60s hoặc sau mỗi thao tác)
    Store->>BE: GET /api/v1/production/pda/cnc-stations
    BE-->>Store: Danh sách máy & trạng thái slot (POS1, POS2)
    Store-->>PDA: Render giao diện (TRỐNG, AMR ĐANG TỚI, ĐANG GIA CÔNG)

    rect rgb(235, 245, 255)
    Note over CNC,AMR: THAO TÁC 1: GỌI PHÔI (Context-Aware: Chọn Model nếu máy đa năng / 1-chạm nếu máy đơn model - Xem ADR-002)
    CNC->>PDA: Bấm "GỌI PHÔI (ĐIỀU AMR ĐẾN)" tại POS1
    alt Máy được gán >= 2 Model (ADR-002)
        PDA-->>CNC: Hiển thị popup chọn Model (VD: Model A hoặc Model B)
        CNC->>PDA: Chọn Model (item_id: 88)
    else Máy chỉ có 1 Model duy nhất
        PDA->>PDA: Tự động chọn Model duy nhất đó
    end
    PDA->>BE: POST /call-material {destination_location_id: 101, item_id: 88}
    BE->>Dispatch: Xác thực máy thuộc Route của item_id -> Lấy required_stage_level
    Dispatch->>AMR: Tìm khay phù hợp & tạo lệnh điều xe AMR chạy tới POS1
    BE-->>PDA: Thành công -> Slot chuyển ngay sang "AMR ĐANG TỚI"
    end

    rect rgb(235, 255, 235)
    Note over CNC,AMR: THAO TÁC 2: BÁO XONG (Nâng level / AMR tới bốc đi từ chính slot đó)
    CNC->>PDA: Bấm "BÁO XONG: CẬP NHẬT LEVEL" tại POS1
    PDA->>BE: POST /complete-stage {location_id: 101}
    BE->>Dispatch: Cập nhật ItemStock nâng Level gia công
    alt Là công đoạn CNC cuối cùng (Level 3)
        Dispatch->>AMR: Điều AMR tới chính POS1 bốc khay chở sang khu Rửa (WASH)
    else Còn công đoạn tiếp theo
        Dispatch->>AMR: Điều AMR tới chính POS1 bốc khay sang máy công đoạn kế
    end
    BE-->>PDA: Thành công -> Slot POS1 chuyển về trạng thái TRỐNG
    end
```

---

## 4. Hình minh họa giao diện PDA thực tế (Wireframe 4.2-inch)

Giao diện thực tế trong [`CncLineModal.tsx`](file:///d:/KuKA/KUKA_WMS/frontend/src/components/pda/CncLineModal.tsx):

```
+-------------------------------------------------------------+
| [KUKA WMS] DÂY CHUYỀN CNC                 [Ca 1] [Đăng Xuất]|
| Quản Lý Trạm Máy Gia Công | Trạm: CNC KUKA AREA 01          |
| Trạng thái: [Online - 60s]                                  |
+-------------------------------------------------------------+
|                                                             |
| [ CNC-01 (Vị trí 1) ] [P1] [Level 1: Phay Thô]              |
| Trạng thái: [ ĐANG GIA CÔNG ]                               |
| ----------------------------------------------------------- |
|   Mã Rack : RACK-0089                                       |
|   Model   : TAY-NẮM-CỬA-V1                                  |
|   Hiện tại: Level 0: Phôi Thô  -->  Đích: Level 1           |
|                                                             |
| +---------------------------------------------------------+ |
| |        [V] BÁO XONG: CẬP NHẬT LEVEL 1                   | |
| +---------------------------------------------------------+ |
|                                                             |
| [ CNC-01 (Vị trí 2) ] [P2] [Level 1: Phay Thô]              |
| Trạng thái: [ TRỐNG ]                                       |
| ----------------------------------------------------------- |
|   Đầu vào yêu cầu: Level 0 (Phôi thô)                       |
|                                                             |
| +---------------------------------------------------------+ |
| |        [+] GỌI PHÔI (ĐIỀU AMR ĐẾN)                      | |
| |             (1-Chạm: Tự động theo Route)                | |
| +---------------------------------------------------------+ |
|                                                             |
| [ CNC-02 (Vị trí 1) ] [P1] [Level 2: Phay Tinh]             |
| Trạng thái: [ AMR ĐANG TỚI ]                                |
| ----------------------------------------------------------- |
|   Model yêu cầu: Phôi tiêu chuẩn                            |
|                                                             |
| +---------------------------------------------------------+ |
| |        [!] Mô phỏng: AMR Đã Cập Bến                     | |
| +---------------------------------------------------------+ |
+-------------------------------------------------------------+
```

---

## 5. Bảng ma trận trạng thái Slot

| Trạng thái Slot | Trạng thái hiển thị PDA | Nút bấm thao tác | Hành vi hệ thống & AMR |
| :--- | :--- | :--- | :--- |
| **`EMPTY`** | **TRỐNG** *(Nền xám)* | **`GỌI PHÔI (ĐIỀU AMR ĐẾN)`** *(Xanh dương lớn)* | Gửi `destination_location_id`. Backend tự suy ra Model & Level yêu cầu từ Route của máy $\rightarrow$ Điều AMR chở phôi đến đúng vị trí này. |
| **`CALLING`** | **AMR ĐANG TỚI** *(Nền hổ phách)* | **`Mô phỏng: AMR Đã Cập Bến`** *(Dùng khi test)* | Giả lập sự kiện AMR đã cập bến và hạ khay phôi vào slot. |
| **`OCCUPIED`** | **ĐANG GIA CÔNG** *(Nền xanh lục)* | **`BÁO XONG: CẬP NHẬT LEVEL...`** *(Xanh lá/Cam)* | Cập nhật tăng Level gia công cho khay. Nếu là bước cuối $\rightarrow$ Tự động điều xe AMR đến **chính slot này** để bốc khay sang khu rửa `WASH`. |

---

## 6. Phân quyền trạm (RBAC) đã cập nhật

Sau các chỉnh sửa phân quyền gần nhất:
1. **Lấy danh sách máy (`GET /cnc-stations`):** Backend chỉ trả về các máy và vị trí thuộc `UserLocation` của công nhân đăng nhập (Admin thấy toàn bộ).
2. **Bảo vệ thao tác gọi phôi & báo xong:** Hàm `_ensure_user_can_access_location` trực tiếp kiểm tra quyền trước khi tạo lệnh điều xe, ngăn chặn tuyệt đối việc bấm nhầm vào máy không thuộc trách nhiệm.
