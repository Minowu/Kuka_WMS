# Bảng Kiểm Kê Cổng WMS & Ma Trận Xung Đột Với KUKA Fleet Manager

Tài liệu này cung cấp bảng kiểm kê chi tiết toàn bộ các cổng mạng mà hệ thống **KUKA_WMS** sử dụng, phân tích ma trận xung đột với **KUKA Fleet Manager**, và đưa ra kế hoạch phân bổ cổng chuẩn hóa cho môi trường Production trên Linux.

---

## 1. Bảng Kiểm Kê Toàn Bộ Cổng Mạng Của KUKA_WMS

### 1.1. Bảng tổng hợp cổng từ cấu hình mã nguồn và Docker Compose

| STT | Dịch vụ (Service) | Container Name | Host Port | Container Port | Giao thức | Phạm vi Listen (Binding) | Expose LAN? | File cấu hình nguồn (file:line) | Ghi chú vai trò |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **PostgreSQL** | `wms-db` | **`5433`** | `5432` | TCP | `0.0.0.0` / `::` | **CÓ** (Nguy cơ) | `docker-compose.yml:9-10` | CSDL chính (`WMS_db`). Dùng port host `5433` để tránh trùng PG 5432 mặc định. |
| **2** | **Redis** | `redis-wms` | **`6379`** | `6379` | TCP | `0.0.0.0` / `::` | **CÓ** (Nguy cơ) | `docker-compose.yml:24-25` | Cache, Celery Broker (`/1`), Celery Backend (`/2`). Không có mật khẩu. |
| **3** | **Backend API** | `wms-backend` | **`8001`** | `8000` | TCP | `0.0.0.0` / `::` | **CÓ** (Cần thiết) | `docker-compose.yml:37-38`, `backend/Dockerfile:14` | FastAPI Uvicorn Server, phục vụ REST API và WebSocket cho PDA & Web. |
| **4** | **Celery Logic** | `wms-celery-logic` | *Không* | `8000` *(int)*| TCP | Nội bộ Docker | Không | `docker-compose.yml:60-70` | Worker xử lý queue `logic` (concurrency=4). Container port 8000 thừa kế từ image. |
| **5** | **Celery Status**| `wms-celery-status`| *Không* | `8000` *(int)*| TCP | Nội bộ Docker | Không | `docker-compose.yml:91-101` | Worker xử lý queue `status` (concurrency=2). |
| **6** | **Celery Fleet** | `wms-celery-fleet` | *Không* | `8000` *(int)*| TCP | Nội bộ Docker | Không | `docker-compose.yml:121-131`| Worker xử lý queue `fleet` (concurrency=4). Giao tiếp ngoại vi với KUKA. |
| **7** | **Celery Beat**  | `wms-celery-beat`  | *Không* | *Không* | - | Nội bộ Docker | Không | `docker-compose.yml:151-157`| Bộ định thời (Scheduler) quét hàng đợi 5s và quét task 15s. |
| **8** | **Frontend Web** | `wms-frontend` | **`5173`** | `80` | TCP | `0.0.0.0` / `::` | **CÓ** (Cần thiết) | `docker-compose.yml:184-185`, `frontend/Dockerfile:15` | Nginx Alpine phục vụ giao diện React build tĩnh cho Admin & PDA. |
| **9** | **Frontend Dev** | *(Tiến trình Node)*| **`5173`** | - | TCP | `0.0.0.0` / `::` | **CÓ** | `frontend/vite.config.ts:22` | Vite Dev Server (khi chạy `npm run dev` trên máy dev, `host: true`). |
| **10**| **Prometheus**   | `prometheus` | **`9090`** | `9090` | TCP | `0.0.0.0` / `::` | **CÓ** (Nên chặn) | `opt/monitoring/docker-compose.yml:7` | Thu thập metrics độ trễ, CPU, RAM, API calls. |
| **11**| **Loki**         | `loki` | **`3100`** | `3100` | TCP | `0.0.0.0` / `::` | **CÓ** (Nên chặn) | `opt/monitoring/docker-compose.yml:23` | Lưu trữ tập trung structured logs từ Alloy. Nội bộ có gRPC `9096`. |
| **12**| **Grafana Alloy**| `alloy` | **`12345`**| `12345`| TCP | `0.0.0.0` / `::` | **CÓ** (Nên chặn) | `opt/monitoring/docker-compose.yml:44` | OpenTelemetry & Loki log pipeline collector (HTTP UI / Metrics). |
| **13**| **Grafana**      | `grafana` | **`3000`** | `3000` | TCP | `0.0.0.0` / `::` | **CÓ** (Nội bộ) | `opt/monitoring/docker-compose.yml:53` | Dashboard trực quan hóa giám sát hệ thống. |
| **14**| **PG Exporter**  | `postgres-exporter`| **`9187`** | `9187` | TCP | `0.0.0.0` / `::` | **CÓ** (Nội bộ) | `opt/monitoring/docker-compose.yml:73` | Exporter metrics CSDL PostgreSQL (Tùy chọn). |
| **15**| **Redis Exporter**| `redis-exporter` | **`9121`** | `9121` | TCP | `0.0.0.0` / `::` | **CÓ** (Nội bộ) | `opt/monitoring/docker-compose.yml:83` | Exporter metrics Redis (Tùy chọn). |

> [!NOTE]
> **Cổng Outbound (WMS gọi ra ngoài)**: WMS kết nối đến **KUKA Fleet Manager** tại cổng **`10870`** (`http://<kuka-fleet-ip>:10870/interfaces/api`) theo cấu hình tại [`backend/app/core/config.py:48`](file:///D:/KuKA/KUKA_WMS/backend/app/core/config.py#L48). WMS không chiếm quyền lắng nghe cổng này trên host, mà gửi request ra ngoài.

### 1.2. Hiện trạng lắng nghe thực tế trên máy Windows (Live Listeners Audit)

Quét thực tế bằng lệnh `Get-NetTCPConnection -State Listen` và `docker ps` ghi nhận:
- **Docker Containers đang chạy và chiếm cổng host**:
  - `wms-db`: Lắng nghe trên `0.0.0.0:5433` và `[::]:5433`
  - `redis-wms`: Lắng nghe trên `0.0.0.0:6379` và `[::]:6379`
  - `grafana`: Lắng nghe trên `0.0.0.0:3000` và `[::]:3000`
  - `loki`: Lắng nghe trên `0.0.0.0:3100` và `[::]:3100`
  - `prometheus`: Lắng nghe trên `0.0.0.0:9090` và `[::]:9090`
  - `alloy`: Lắng nghe trên `0.0.0.0:12345` và `[::]:12345`
- **Tiến trình chạy trực tiếp trên Windows Host (không qua Docker)**:
  - `0.0.0.0:8001`: Python Uvicorn (FastAPI Backend, PID 14952)
  - `[::]:5173`: Node.js Vite Dev Server (Frontend, PID 31336)
  - `0.0.0.0:5432`: PostgreSQL cục bộ của Windows (PID 7124)

---

## 2. Danh Sách Cổng Của KUKA Fleet Manager Cần Tránh

Theo đặc tả của nhà sản xuất KUKA (KUKA Navigation & Fleet Management Suite):

| Nhóm chức năng | Cổng mạng (Port) | Giao thức | Mô tả / Vai trò trong KUKA Fleet |
| :--- | :--- | :--- | :--- |
| **Web UI** | **`5000`** | TCP (HTTP) | Web Dashboard quản trị KUKA Fleet mặc định |
| | **`5443`** | TCP (HTTPS) | Web Dashboard quản trị bảo mật HTTPS |
| | **`443`** | TCP (HTTPS) | Cổng chuẩn HTTPS trên KUKA Fleet phiên bản 2.16 |
| | **`80`** | TCP (HTTP) | Cổng chuẩn HTTP trên KUKA Fleet phiên bản 2.14 |
| | **`8088`** | TCP (HTTP) | Giao diện Web Portal bổ trợ trên phiên bản 2.16 |
| **Integration** | **`10870`** | TCP (HTTP) | **KUKA Interface**: Cổng API tiếp nhận nhiệm vụ từ WMS/MES |
| | **`7998`** | TCP (gRPC) | KUKA WCS gRPC Interface kết nối thời gian thực |
| | **`8081`** | TCP (HTTP) | WCS HTTP Interface dành riêng cho PDA / Handheld của KUKA |
| | **`8082`** | TCP (HTTP) | ECS Swagger / API Documentation trên bản 2.16 |
| **Robots / PLC** | **`8988`** | UDP | Giao thức định vị, telemetry và broadcast trạng thái robot AMR |
| | **`8883`** | TCP (MQTTS) | MQTT Broker bảo mật kết nối trực tiếp với robot KUKA |
| | **`2883`** | TCP (MQTT) | MQTT Broker kết nối PLC / Trạm sạc / Trạm cân ECS |
| **Internal** | **`10873`** | TCP | KUKA Cluster / Internal Node Sync |
| | **`123` / `1234`**| UDP (NTP) | **NTP Time Server**: Đồng bộ mili-giây tuyệt đối cho toàn bộ AMR |
| | **`50090`** | TCP | KUKA Core Dispatcher internal service |
| | **`50200`** | TCP | KUKA Map Engine & Path Planning service |

---

## 3. Ma Trận So Khớp & Đánh Giá Xung Đột (Conflict Matrix)

### 3.1. Bảng so khớp trực tiếp giữa Cổng WMS và Cổng KUKA Fleet

| Cổng WMS | Dịch vụ WMS | So khớp với cổng KUKA Fleet | Trùng số hiệu? | Nguy cơ tiềm ẩn | Đánh giá rủi ro |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`5433`** | PostgreSQL | So với `5443` (Fleet HTTPS), `5432` | **KHÔNG** | Rất gần `5443` (dễ nhầm khi gõ cấu hình) | Thấp |
| **`6379`** | Redis | Không có trong danh mục KUKA | **KHÔNG** | Mở ra 0.0.0.0 không có password sẽ bị quét | Trung bình (Bảo mật) |
| **`8001`** | WMS Backend API | So với `8081` (WCS PDA), `8082` (Swagger), `8088` | **KHÔNG** | Không trùng số hiệu | An toàn |
| **`5173`** | WMS Frontend Web | So với `5000` (Web UI), `80`, `443` | **KHÔNG** | Nếu đổi sang port 80/443 trên host sẽ xung đột ngay | Thấp (nếu giữ 5173) |
| **`3000`** | Grafana | Không có trong danh mục KUKA | **KHÔNG** | Không trùng | An toàn |
| **`3100`** | Loki | Không có trong danh mục KUKA | **KHÔNG** | Không trùng | An toàn |
| **`9090`** | Prometheus | Không có trong danh mục KUKA | **KHÔNG** | Không trùng | An toàn |
| **`12345`**| Grafana Alloy | So với UDP `1234` (KUKA NTP) | **KHÔNG** | Khác giao thức (TCP vs UDP) và khác số hiệu (12345 vs 1234) | Thấp |
| **`9187`** | Postgres-Exporter| Không có trong danh mục KUKA | **KHÔNG** | Không trùng | An toàn |
| **`9121`** | Redis-Exporter | Không có trong danh mục KUKA | **KHÔNG** | Không trùng | An toàn |
| *Outbound* | Client HTTP Call | Cổng **`10870`** trên KUKA Fleet | **KHÔNG** | WMS là Client gọi đến KUKA, không bind server | An toàn |

> [!IMPORTANT]
> **KẾT LUẬN XUNG ĐỘT TRỰC TIẾP**:
> **HIỆN TẠI KHÔNG CÓ BẤT KỲ CỔNG NÀO CỦA WMS BỊ TRÙNG SỐ HIỆU (0 PORT CONFLICTS)** với danh mục cổng của KUKA Fleet Manager trên cấu hình cổng Host mặc định.

---

### 3.2. Phân tích theo 2 kịch bản triển khai

#### Kịch bản A: Chạy CÙNG MÁY CHỦ (Co-located / Same Host với KUKA Fleet Manager)
Nếu WMS và KUKA Fleet Manager được cài đặt trên cùng một máy chủ vật lý hoặc chung một máy ảo Linux:

> [!CAUTION]
> **4 BẪY NGUY HIỂM CHẾT NGƯỜI CẦN TRÁNH TUYỆT ĐỐI**:
>
> 1. **Bẫy cổng Frontend Nginx (Cổng 80 & 443)**:
>    - Bên trong container `wms-frontend`, Nginx đang lắng nghe trên cổng `80` ([`frontend/Dockerfile:15`](file:///D:/KuKA/KUKA_WMS/frontend/Dockerfile#L15), [`frontend/nginx.conf:2`](file:///D:/KuKA/KUKA_WMS/frontend/nginx.conf#L2)).
>    - Hiện tại compose đang map `5173:80`. Nếu quản trị viên tiện tay sửa thành `"80:80"` hoặc `"443:443"` để người dùng không cần gõ cổng 5173, **nó sẽ lập tức cướp hoặc làm sập KUKA Fleet Web Management Portal** (KUKA dùng cổng 80 trên bản 2.14 và cổng 443 trên bản 2.16).
>    - **Biện pháp**: Bắt buộc giữ cổng Host là `5173` (hoặc cổng riêng như `8443` / `8080`), tuyệt đối cấm bind cổng `80` hoặc `443` trên Host.
>
> 2. **Bẫy dịch vụ NTP Time Sync (UDP 123 / UDP 1234)**:
>    - KUKA Fleet Manager vận hành một NTP Server cục bộ (hoặc phụ thuộc khắt khe vào cổng UDP 123 / 1234) để đồng bộ thời gian từng mili-giây cho các robot AMR di chuyển chống va chạm.
>    - Nếu máy chủ Linux cài đặt dịch vụ `chrony`, `ntpd` hoặc bật NTP Server lắng nghe UDP 123, hai dịch vụ sẽ tranh chấp socket UDP, khiến AMR mất đồng bộ thời gian và dừng khẩn cấp (Emergency Stop).
>    - **Biện pháp**: Máy chủ Linux chứa WMS **không được chạy NTP Server daemon**. Nếu cần đồng bộ giờ, cấu hình `chrony` hoặc `systemd-timesyncd` ở chế độ **NTP Client thuần túy**, trỏ thẳng vào IP của KUKA NTP Server hoặc NTP chung của nhà máy.
>
> 3. **Bẫy mở cổng 0.0.0.0 (Bypass tường lửa Docker)**:
>    - Mọi cổng khai báo dạng `"5433:5432"` hay `"6379:6379"` trong Compose đều mặc định bind vào `0.0.0.0` trên Linux.
>    - Khi đó, cổng CSDL PostgreSQL (5433) và Redis (6379 không có mật khẩu) bị phơi bày ra toàn bộ mạng công nghiệp, nơi các PLC, trạm sạc và thiết bị IoT của KUKA hoạt động.
>    - **Biện pháp**: Trên Linux, bắt buộc cấu hình bind tường minh `127.0.0.1:5433:5432` và `127.0.0.1:6379:6379` để chỉ nội bộ host mới truy cập được.
>
> 4. **Trùng lặp cổng đích KUKA Interface (TCP 10870)**:
>    - KUKA Fleet đã chiếm giữ TCP 10870 để nhận lệnh từ MES/WMS. WMS tuyệt đối không được cấu hình bất kỳ container nào expose cổng `10870`.

#### Kịch bản B: Chạy KHÁC MÁY CHỦ (Dedicated Host riêng trên mạng xưởng LAN)
Nếu WMS triển khai trên máy chủ Linux độc lập (ví dụ `192.168.1.50`), còn KUKA Fleet nằm ở máy chủ khác (ví dụ `192.168.1.71`):
- **Xung đột cổng phần cứng**: Hoàn toàn bằng 0. Mỗi máy có dải cổng riêng.
- **Yêu cầu kết nối mạng (Firewall Routing)**:
  - Máy chủ WMS phải được phép gửi gói tin TCP đến `192.168.1.71:10870` (Gửi nhiệm vụ AMR).
  - Máy chủ KUKA Fleet phải được phép gửi Webhook HTTP POST ngược về `http://192.168.1.50:8001/api/v1/...` (Thông báo trạng thái xe phôi, hoàn thành nhiệm vụ).
  - Các máy PDA cầm tay của công nhân CNC phải truy cập được `http://192.168.1.50:5173` (Frontend) và `http://192.168.1.50:8001` (Backend API).

---

## 4. Kế Hoạch Phân Bổ Cổng Chuẩn Hóa Trên Linux Production

Để đảm bảo hệ thống vừa an toàn, vừa dễ vận hành, toàn bộ cổng dịch vụ trên Linux Server cần được chuẩn hóa như sau:

| Dịch vụ | Container | Host Binding đề xuất | Container Port | Mục đích mở cổng | Chính sách Tường lửa (UFW) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **WMS Frontend** | `wms-frontend` | `0.0.0.0:5173` | `80` | PDA công nhân & Máy tính Quản đốc truy cập | Mở cho dải IP mạng xưởng (LAN) |
| **WMS Backend API** | `wms-backend` | `0.0.0.0:8001` | `8000` | REST API, WebSocket PDA, Webhook từ KUKA Fleet | Mở cho dải IP mạng xưởng (LAN) & KUKA IP |
| **PostgreSQL** | `wms-db` | **`127.0.0.1:5433`** | `5432` | Chỉ cho Backend, Celery và Backup script trên host | **CHẶN MẠNG NGOÀI (Chỉ Localhost)** |
| **Redis** | `redis-wms` | **`127.0.0.1:6379`** | `6379` | Chỉ cho Backend, Celery và Exporter | **CHẶN MẠNG NGOÀI (Chỉ Localhost)** |
| **Grafana** | `grafana` | `0.0.0.0:3000` | `3000` | Kỹ sư vận hành xem dashboard giám sát | Chỉ mở cho IP máy tính Admin/IT |
| **Prometheus** | `prometheus` | **`127.0.0.1:9090`** | `9090` | Thu thập metrics nội bộ, Grafana datasource | **CHẶN MẠNG NGOÀI (Chỉ Localhost)** |
| **Loki** | `loki` | **`127.0.0.1:3100`** | `3100` | Nhận log từ Alloy, Grafana datasource | **CHẶN MẠNG NGOÀI (Chỉ Localhost)** |
| **Grafana Alloy** | `alloy` | **`127.0.0.1:12345`**| `12345`| Đọc log container nội bộ | **CHẶN MẠNG NGOÀI (Chỉ Localhost)** |
| **Postgres Exporter**| `postgres-exporter`| *Không expose host* | `9187` | Nằm chung Docker network `wms-net` với Prometheus | Không cần map ra host |
| **Redis Exporter** | `redis-exporter` | *Không expose host* | `9121` | Nằm chung Docker network `wms-net` với Prometheus | Không cần map ra host |
| **Celery Workers** | Tất cả workers | *Không có port host*| - | Kết nối trực tiếp qua Docker network | Không cần port |

---

## 5. Tóm Tắt Quy Tắc Vàng Khi Cấu Hình Cổng (Golden Rules)

1. **Tuyệt đối KHÔNG gán cổng `80` hoặc `443` cho Nginx WMS trên Host** nếu máy chủ có KUKA Fleet Manager.
2. **Luôn chỉ định IP `127.0.0.1:` trước cổng nội bộ** (`127.0.0.1:5433:5432`, `127.0.0.1:6379:6379`) để ngăn Docker mở toang cổng CSDL ra toàn mạng xưởng.
3. **Cấm tuyệt đối kích hoạt NTP Server daemon (UDP 123/1234)** trên máy chủ WMS nếu chia sẻ chung hệ điều hành với KUKA Fleet.
4. **Giữ nguyên cổng `8001` cho Backend và `5173` cho Frontend** để đồng bộ với cấu hình PDA và logic webhook đã kiểm thử.
