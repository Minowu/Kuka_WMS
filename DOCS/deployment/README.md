# Tài Liệu Triển Khai & Di Chuyển Hệ Thống KUKA_WMS Sang Linux

Tài liệu này cung cấp hướng dẫn tổng thể, phân tích xung đột hạ tầng và quy trình từng bước để di chuyển toàn bộ hệ thống **KUKA_WMS** từ môi trường máy tính Windows hiện tại sang máy chủ Linux chuyên dụng (Ubuntu Server / Debian), đảm bảo an toàn dữ liệu sản xuất và **tuyệt đối không xung đột cổng mạng với KUKA Fleet Manager**.

---

## 1. Mục Tiêu & Phạm Vi (Scope & Objectives)

1. **Chuẩn hóa hạ tầng triển khai**: Chuyển đổi từ môi trường phát triển lai (lai giữa Docker và tiến trình chạy trực tiếp trên Windows) sang 100% Docker Container trên Linux Server.
2. **Triệt tiêu xung đột cổng mạng**: Rà soát, so khớp ma trận cổng mạng của KUKA_WMS với KUKA Fleet Manager (Web UI, API tích hợp, Robot AMR, MQTT, NTP, PLC).
3. **Sửa chữa các lỗi tiềm ẩn của Compose**: Khắc phục các sai lệch về cấu hình kết nối CSDL, connection pool, phân giải DNS nội bộ, quyền ghi file log và định dạng ký tự kết thúc dòng (CRLF/LF).
4. **Bảo toàn dữ liệu sản xuất**: Di chuyển toàn vẹn dữ liệu PostgreSQL (`WMS_db`), bộ nhớ đệm Redis AOF, và cấu hình giám sát Grafana/Loki.

---

## 2. Bản Đồ Tài Liệu (Documentation Roadmap)

Bộ tài liệu triển khai được chia làm 3 tài liệu chuyên sâu:

```
DOCS/deployment/
├── README.md                      # [Tài liệu hiện tại] Tổng quan, kiến trúc và điều hướng
├── 01-port-matrix.md              # Kiểm kê cổng WMS, ma trận xung đột KUKA Fleet & quy hoạch cổng
├── 02-linux-migration-guide.md    # Hướng dẫn chi tiết từng bước di chuyển từ Windows sang Linux
└── 03-pre-migration-checklist.md   # Danh mục kiểm tra tiền di chuyển & sửa lỗi compose (file:line)
```

### Chi tiết từng tài liệu:
- **[`01-port-matrix.md`](01-port-matrix.md)**:
  - Bảng kiểm kê chi tiết tất cả các cổng mạng WMS đang sử dụng (Host port, Container port, Listen Address, cấu hình nguồn).
  - So khớp ma trận xung đột với toàn bộ cổng của KUKA Fleet Manager theo 2 kịch bản: **Chạy chung máy chủ (Co-located)** và **Chạy máy chủ riêng biệt (Dedicated Host)**.
  - Cảnh báo các bẫy rủi ro nghiêm trọng (Nginx container port 80, mở cổng 0.0.0.0, NTP UDP 123/1234).
  - Quy hoạch cổng chuẩn hóa cho môi trường Production trên Linux.
- **[`02-linux-migration-guide.md`](02-linux-migration-guide.md)**:
  - Hướng dẫn cài đặt môi trường Linux từ đầu (Docker Engine, Docker Compose v2, UFW).
  - Quy trình sao lưu dữ liệu từ Windows (`pg_dump` qua cổng 5433, Redis AOF snapshot) và khôi phục trên Linux.
  - Thiết lập mạng Docker dùng chung (`wms-net`) kết nối WMS Core và Monitoring Stack.
  - Cấu hình tường lửa UFW (tránh bẫy Docker iptables bypass), Log Rotation, Auto-restart systemd và Kịch bản Rollback khẩn cấp.
- **[`03-pre-migration-checklist.md`](03-pre-migration-checklist.md)**:
  - Danh mục kiểm tra dạng checkbox (`[ ]`) chi tiết cho Quản trị viên hệ thống và Kỹ sư DevOps.
  - Bảng kiểm kê 12 lỗi cấu hình đã phát hiện trong file `docker-compose.yml`, `opt/monitoring/docker-compose.yml`, `backend/.env`, kèm chính xác vị trí `file:line` và câu lệnh/cách sửa mẫu.

---

## 3. Kiến Trúc Triển Khai Hệ Thống KUKA_WMS Trên Linux

Hệ thống được đóng gói thành 2 Compose project kết nối với nhau qua Docker bridge network ngoài (`wms-net`):

```
                                  MẠNG NỘI BỘ NHÀ XƯỞNG (LAN)
                                              │
              ┌───────────────────────────────┴───────────────────────────────┐
              │                                                               │
     [PDA Màn hình 4.2" / Web Quản trị]                             [KUKA Fleet Manager]
              │ (TCP 5173 / HTTP)                                             │ (TCP 10870)
              ▼                                                               ▼
┌───────────────────────────────────────────────┐               ┌──────────────────────────┐
│ LINUX SERVER HOST                             │               │ KUKA FLEET HOST / VM     │
│                                               │               │                          │
│  ┌─────────────────────────────────────────┐  │               │ - Web UI: 5000 / 5443    │
│  │ DOCKER BRIDGE NETWORK: wms-net          │  │               │ - Integration: 10870     │
│  │                                         │  │   HTTP POST   │ - WCS gRPC: 7998         │
│  │  [wms-frontend] (Nginx :80 ──> Host 5173│  │ ────────────> │ - WCS HTTP: 8081        │
│  │         │                               │  │ (Submit Task) │ - MQTT Robots: 8883      │
│  │         ▼                               │  │               │ - NTP Server: UDP 123    │
│  │  [wms-backend] (Uvicorn :8000 ──> 8001) ──┼──┘               └──────────────────────────┘
│  │         │                               │
│  │    ┌────┴────────────────────────┐      │
│  │    ▼                             ▼      │
│  │ [wms-db] (PG 16)         [redis-wms]    │
│  │ (Port 5432 ──> 127.0.0.1:5433)   (:6379)│
│  │    ▲                             ▲      │
│  │    │ ┌───────────────────────────┤      │
│  │    │ │                           │      │
│  │  [Celery Workers & Beat]         │      │
│  │  - wms-celery-logic              │      │
│  │  - wms-celery-status             │      │
│  │  - wms-celery-fleet              │      │
│  │  - wms-celery-beat               │      │
│  │                                  │      │
│  │  ─────────────────────────────── │      │
│  │  MONITORING STACK                │      │
│  │  - [alloy]       (Log Shipper)   │      │
│  │  - [loki]        (:3100)         │      │
│  │  - [prometheus]  (:9090) ◄───────┘      │
│  │  - [grafana]     (:3000)                │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

---

## 4. Tóm Tắt Các Điểm Rủi Ro Hàng Đầu Cần Lưu Ý

1. **Xung đột cổng với KUKA Fleet**: Hiện tại với cấu hình cổng mặc định, **không có xung đột trực tiếp**. Tuy nhiên, nếu triển khai chung máy chủ (Co-located), tuyệt đối không để Frontend Nginx lắng nghe hoặc forward cổng `80` hay `443` lên Host, và không chạy NTP server daemon trên Linux (tránh tranh chấp UDP `123`).
2. **Lỗi duplicate `WMS_DB_ROLE`**: Trong `docker-compose.yml`, dịch vụ `backend` bị khai báo trùng `WMS_DB_ROLE: celery` đè lên `backend`, khiến API chạy với connection pool chỉ có 2 connection, gây nghẽn toàn bộ PDA khi xưởng hoạt động.
3. **Sai tên CSDL `kuka` vs `WMS_db`**: Nhiều nơi trong `docker-compose.yml` và `.env` đang khai báo kết nối vào CSDL tên `kuka`, trong khi Postgres khởi tạo CSDL `WMS_db`, sẽ gây sập Backend ngay khi khởi động.
4. **Phân quyền Log Directory trên Linux**: Grafana Alloy chạy dưới user nội bộ không có quyền đọc thư mục `backend/logs` nếu thư mục này tạo bởi user `root` trên Linux.
5. **Định dạng xuống dòng Windows (CRLF)**: Toàn bộ script hoặc cấu hình chuyển từ Windows sang Linux cần được chuyển về LF để tránh lỗi thực thi `/bin/sh^M`.
