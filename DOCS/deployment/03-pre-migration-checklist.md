# Danh Mục Kiểm Tra Tiền Di Chuyển Lên Linux (Pre-Migration Checklist)

Tài liệu này tổng hợp toàn bộ các vấn đề kỹ thuật được phát hiện trong đợt kiểm toán (Audit) cấu hình của **KUKA_WMS**, cung cấp vị trí chính xác `file:line`, nguyên nhân lỗi, giải pháp khắc phục (Recommended Fix), và danh mục kiểm tra (Checklist) trước khi thực hiện triển khai chính thức trên máy chủ Linux.

> [!IMPORTANT]
> **QUY TẮC AN TOÀN**: Tài liệu này chỉ dùng để ghi nhận và hướng dẫn khắc phục. **Không trực tiếp chỉnh sửa các file mã nguồn hiện tại** cho tới khi có phê duyệt kế hoạch triển khai chính thức.

---

## 1. Bảng Tổng Hợp Lỗi Cấu Hình & Khuyến Nghị Khắc Phục (Issues Audit)

| Mã lỗi | Vấn đề phát hiện | Vị trí chính xác (`file:line`) | Hậu quả kỹ thuật | Khuyến nghị khắc phục (Recommended Fix) |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | **Duplicate key `WMS_DB_ROLE`** trong dịch vụ `backend` | [`docker-compose.yml:42-43`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L42-L43) | Trong chuẩn YAML, key viết sau ghi đè key trước. API nhận giá trị `celery`, bị gán pool kết nối chỉ có 2 connection ([`database.py:16`](file:///D:/KuKA/KUKA_WMS/backend/app/core/database.py#L16)), gây nghẽn và timeout ngay lập tức khi 40+ PDA kết nối. | Xóa dòng 43 (`WMS_DB_ROLE: celery`), chỉ giữ lại dòng 42 `WMS_DB_ROLE: backend`. |
| **BUG-02** | **Sai lệch tên CSDL** (`kuka` vs `WMS_db`) | [`docker-compose.yml:44,75,106,136,162`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L44), [`backend/.env:5`](file:///D:/KuKA/KUKA_WMS/backend/.env#L5) | Compose khởi tạo CSDL tên `WMS_db` ([`L8`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L8)), healthcheck kiểm tra `WMS_db` ([`L16`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L16)), nhưng `DATABASE_URL` trong Backend và Celery lại trỏ vào `/kuka`. Trên container mới sẽ báo lỗi `FATAL: database "kuka" does not exist`. | Đổi toàn bộ chuỗi kết nối `DATABASE_URL` từ `/kuka` thành `/WMS_db`. |
| **BUG-03** | **Dữ liệu phân mảnh giữa 2 CSDL** (`kuka` và `WMS_db`) | Container `wms-db` hiện tại | CSDL `kuka` chứa dữ liệu sản xuất mới nhất (ngày 30/10/2026), trong khi `WMS_db` chỉ có dữ liệu cũ (19/10/2026). Nếu chỉ dump `WMS_db` sẽ làm mất 11 ngày dữ liệu vận hành gần nhất. | Dump dữ liệu từ CSDL `kuka`, sau đó nạp vào CSDL chuẩn hóa `WMS_db` trên Linux. |
| **BUG-04** | **`postgres-exporter` sai cổng host và hardcode IP** | [`opt/monitoring/docker-compose.yml:71`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/docker-compose.yml#L71) | DSN cấu hình `192.168.50.200:5432`, nhưng port host của Postgres thực tế là `5433` (trong container là `5432`). Khi sang Linux, IP này không tồn tại và exporter không kết nối được CSDL. | Đổi thành `postgresql://postgres:${POSTGRES_PASSWORD}@wms-db:5432/WMS_db?sslmode=disable` qua mạng nội bộ Docker `wms-net`. |
| **BUG-05** | **Prometheus scrape fail DNS** (Khác Docker Network) | [`opt/monitoring/docker-compose.yml`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/docker-compose.yml), [`opt/monitoring/prometheus/prometheus.yml:15,22,26`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/prometheus/prometheus.yml#L15) | File compose chính và compose monitoring là 2 project riêng biệt, mặc định nằm ở 2 Docker network khác nhau. Prometheus không phân giải được tên container `wms-backend`, `postgres-exporter` nếu không chung network. | Khai báo chung một mạng ngoài `networks: wms-net: external: true` trong cả 2 file Compose. |
| **BUG-06** | **`host.docker.internal` không phân giải được trên Linux** | [`opt/monitoring/prometheus/prometheus.yml:15`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/prometheus/prometheus.yml#L15), [`docker-compose.yml`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml) | Trên Linux Docker Engine, `host.docker.internal` không tự động có sẵn như Windows/macOS nếu thiếu chỉ thị `extra_hosts`. Prometheus sẽ báo lỗi connection refused / host not found. | Thêm `extra_hosts: - "host.docker.internal:host-gateway"` hoặc tốt nhất là trỏ thẳng qua DNS container `wms-backend:8000`. |
| **BUG-07** | **Frontend build arg `VITE_API_URL` bị hardcode cứng** | [`docker-compose.yml:182`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L182) | Cấu hình cứng `http://192.168.50.200:8001`. Khi đưa lên Linux có IP khác, toàn bộ request từ trình duyệt PDA sẽ gửi về IP cũ và bị lỗi kết nối mạng. | Chuyển thành biến môi trường `VITE_API_URL: ${VITE_API_URL:-http://localhost:8001}` trong file `.env`. |
| **BUG-08** | **Mật khẩu lộ rõ trong Compose & Redis không bảo mật** | [`docker-compose.yml:7`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L7), [`opt/monitoring/docker-compose.yml:56`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/docker-compose.yml#L56) | Mật khẩu Postgres (`thado123`), Grafana (`Thado123`) bị hardcode trong Git repository. Redis mở không có password trên cổng 6379 ra toàn mạng 0.0.0.0. | Đưa toàn bộ thông tin nhạy cảm vào file `.env` (gitignored), tạo `.env.example` làm mẫu. |
| **BUG-09** | **Phân quyền thư mục logs cho Grafana Alloy trên Linux** | [`opt/monitoring/docker-compose.yml:41`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/docker-compose.yml#L41) | Container `alloy` chạy với UID người dùng nội bộ (thường là `10001` hoặc `nobody`). Khi mount `../../backend/logs:/var/log/wms:ro`, Alloy sẽ bị lỗi `permission denied` nếu thư mục host do `root` sở hữu. | Chạy lệnh `chmod -R 755 backend/logs` trên Linux để Alloy có quyền đọc file `.jsonl`. |
| **BUG-10** | **Định dạng xuống dòng Windows CRLF (`\r\n`)** | Toàn bộ script shell, Dockerfile, config | File tạo trên Windows có ký tự `\r\n`. Khi chạy trong Linux container sẽ sinh lỗi cú pháp hoặc `/bin/sh^M: bad interpreter`. | Chạy công cụ `dos2unix` trên Linux cho toàn bộ file trước khi build. |
| **BUG-11** | **Múi giờ Container và nguy cơ xung đột NTP** | [`docker-compose.yml`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml), Toàn hệ thống | Các container chưa khai báo `TZ=Asia/Ho_Chi_Minh`, dễ dẫn đến lệch mốc thời gian giữa log CSDL và log ứng dụng. Đồng thời, máy chủ KHÔNG ĐƯỢC chạy NTP Server UDP 123/1234 nếu chung máy với KUKA Fleet. | Thêm biến môi trường `TZ: Asia/Ho_Chi_Minh` cho toàn bộ container. Cấu hình máy chủ Linux ở chế độ NTP Client. |
| **BUG-12** | **Không nhất quán tên hàng đợi Celery (Docs vs Code)** | [`backend/app/core/celery_app.py:18-20`](file:///D:/KuKA/KUKA_WMS/backend/app/core/celery_app.py#L18-L20) vs [`vault-docs/constraints.md:21-22`](file:///D:/KuKA/KUKA_WMS/vault-docs/constraints.md#L21-L22) | Code và Compose chạy 3 hàng đợi: `logic`, `status`, `fleet`. Tuy nhiên tài liệu kiến trúc cũ chỉ ghi nhận `logic` và `sync`. Nếu cấu hình worker theo tài liệu cũ sẽ làm nghẽn toàn bộ lệnh KUKA Fleet. | Cập nhật tài liệu kiến trúc khớp với cấu hình thực tế (`logic`, `status`, `fleet`). |
| **BUG-13** | **Mở cổng 0.0.0.0 bypass tường lửa trên Linux** | [`docker-compose.yml:9,24`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml#L9), [`opt/monitoring/docker-compose.yml`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/docker-compose.yml) | Docker tự chèn rule vào iptables mở thông cổng 5433, 6379, 3100, 9090 ra mạng xưởng. Bất kỳ máy nào trong mạng LAN cũng có thể truy cập thẳng CSDL và Redis không password. | Đổi cấu hình port mapping thành `127.0.0.1:5433:5432`, `127.0.0.1:6379:6379` để chỉ nội bộ host truy cập được. |
| **BUG-14** | **Thiếu cấu hình Docker Log Rotation** | [`docker-compose.yml`](file:///D:/KuKA/KUKA_WMS/docker-compose.yml), [`opt/monitoring/docker-compose.yml`](file:///D:/KuKA/KUKA_WMS/opt/monitoring/docker-compose.yml) | Các container không giới hạn dung lượng log (`max-size`, `max-file`), theo thời gian file json log tại `/var/lib/docker/containers/` sẽ làm tràn phân vùng đĩa cứng máy chủ. | Thêm `logging: options: max-size: "50m", max-file: "3"` vào từng dịch vụ hoặc cấu hình tập trung tại `/etc/docker/daemon.json`. |

---

## 2. Danh Mục Kiểm Tra Từng Bước (Migration Checklist)

### Giai đoạn 1: Chuẩn bị mã nguồn & Sửa cấu hình (Pre-flight Config Fixes)
- [ ] **Sửa BUG-01**: Mở `docker-compose.yml`, tại dịch vụ `backend`, **xóa bỏ** dòng `WMS_DB_ROLE: celery`, giữ lại `WMS_DB_ROLE: backend`.
- [ ] **Sửa BUG-02**: Đổi toàn bộ chuỗi kết nối `DATABASE_URL` trong `docker-compose.yml` (các dịch vụ `backend`, `celery-worker-logic`, `celery-worker-status`, `celery-worker-fleet`, `celery-beat`) sang `postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/WMS_db`.
- [ ] **Sửa BUG-07**: Trong `docker-compose.yml`, cập nhật build arg `frontend`:
  ```yaml
  args:
    VITE_API_URL: ${VITE_API_URL:-http://localhost:8001}
  ```
- [ ] **Sửa BUG-04 & BUG-05**: Trong `opt/monitoring/docker-compose.yml`:
  - Thêm network dùng chung:
    ```yaml
    networks:
      wms-net:
        external: true
    ```
  - Cập nhật dịch vụ `postgres-exporter`:
    ```yaml
    environment:
      DATA_SOURCE_NAME: "postgresql://postgres:${POSTGRES_PASSWORD}@wms-db:5432/WMS_db?sslmode=disable"
    networks:
      - wms-net
    ```
  - Cập nhật `prometheus` kết nối vào `wms-net`.
- [ ] **Sửa BUG-13**: Chuyển các cổng nội bộ sang bind `127.0.0.1`:
  - `wms-db`: `"127.0.0.1:5433:5432"`
  - `redis-wms`: `"127.0.0.1:6379:6379"`
  - `prometheus`: `"127.0.0.1:9090:9090"`
  - `loki`: `"127.0.0.1:3100:3100"`
  - `alloy`: `"127.0.0.1:12345:12345"`
- [ ] **Sửa BUG-11**: Thêm `TZ: "Asia/Ho_Chi_Minh"` vào `environment` của toàn bộ các service trong 2 file compose.
- [ ] **Kiểm tra cổng Frontend Nginx**: Xác nhận cổng container `80` chỉ map ra Host port `5173` (hoặc cổng reverse proxy tùy chọn), **tuyệt đối không map `80:80` hay `443:443`**.

---

### Giai đoạn 2: Chuẩn bị máy chủ đích Linux (Server Preparation)
- [ ] Cài đặt Docker Engine 24+ và Docker Compose v2 plugin (`docker compose`).
- [ ] Cấu hình `/etc/docker/daemon.json` với chính sách log rotation (`max-size: 50m`, `max-file: 3`).
- [ ] Tạo Docker bridge network ngoài: `docker network create wms-net`.
- [ ] Kiểm tra tường lửa máy chủ:
  - Cổng 22 (SSH): Cho phép.
  - Cổng 5173 (Frontend): Mở cho dải IP xưởng sản xuất.
  - Cổng 8001 (Backend API & Webhook KUKA): Mở cho dải IP xưởng và IP máy chủ KUKA Fleet.
  - Cổng 3000 (Grafana): Chỉ mở cho dải IP máy tính quản trị.
  - Các cổng 5433, 6379, 3100, 9090: Đảm bảo không mở ra Internet/LAN bên ngoài.
- [ ] **Kiểm tra NTP Server**: Xác nhận trên máy chủ Linux KHÔNG cài đặt hoặc kích hoạt NTP Server lắng nghe cổng UDP 123 hoặc 1234 (tránh xung đột với KUKA Fleet NTP Server). Cấu hình máy chủ Linux làm NTP client đồng bộ về NTP Server của nhà máy.

---

### Giai đoạn 3: Sao chép & Chuyển đổi dữ liệu (Data & Source Transfer)
- [ ] Đóng gói mã nguồn từ Windows loại trừ `.venv`, `node_modules`, `scratch`, `__pycache__`.
- [ ] Chuyển file sang Linux và giải nén tại `/opt/kuka_wms`.
- [ ] **Sửa BUG-10**: Chạy `dos2unix` trên toàn bộ file shell script, yaml, env trên Linux:
  ```bash
  find /opt/kuka_wms -type f \( -name "*.sh" -o -name "*.env*" -o -name "*.yml" -o -name "*.yaml" -o -name "*.alloy" \) -exec dos2unix {} +
  ```
- [ ] **Sửa BUG-09**: Phân quyền thư mục logs và uploads:
  ```bash
  mkdir -p /opt/kuka_wms/backend/logs /opt/kuka_wms/backend/uploads
  chmod -R 777 /opt/kuka_wms/backend/logs
  chmod -R 775 /opt/kuka_wms/backend/uploads
  ```
- [ ] **Sửa BUG-03 (Backup CSDL)**:
  - Trên máy Windows: Chạy lệnh `pg_dump` xuất toàn bộ dữ liệu từ CSDL `kuka` (chứa dữ liệu mới nhất 30/10/2026) ra file `kuka_prod_active.dump`.
  - Đồng thời backup dự phòng CSDL `WMS_db` ra file `wms_db_legacy.dump`.
  - Sao chép 2 file dump sang Linux.
- [ ] **Sao lưu Redis**: Chạy `redis-cli bgsave` trên máy Windows, sao chép file `dump.rdb` sang Linux.

---

### Giai đoạn 4: Triển khai & Khôi phục CSDL (Deployment & Restore)
- [ ] Tạo file `.env` trên Linux với các thông số bảo mật chính thức (mật khẩu mạnh cho Postgres, Grafana, trỏ `DATABASE_URL` vào `WMS_db`, `VITE_API_URL` trỏ IP máy chủ Linux mới).
- [ ] Khởi động trước 2 container `db` và `redis`:
  ```bash
  cd /opt/kuka_wms && docker compose up -d db redis
  ```
- [ ] Đợi `wms-db` chuyển sang trạng thái `healthy`.
- [ ] Khôi phục dữ liệu sản xuất vào CSDL đích `WMS_db`:
  ```bash
  docker exec -i wms-db pg_restore -U postgres -d WMS_db --clean --if-exists -v < /opt/kuka_wms/kuka_prod_active.dump
  ```
- [ ] Truy vấn xác minh dữ liệu:
  ```bash
  docker exec -t wms-db psql -U postgres -d WMS_db -c "SELECT count(*) FROM item_stock;"
  ```
- [ ] Khôi phục file `dump.rdb` vào Redis (nếu cần giữ cache).
- [ ] Build và khởi chạy toàn bộ hệ thống WMS Core:
  ```bash
  docker compose build --no-cache
  docker compose up -d
  ```
- [ ] Khởi chạy Monitoring Stack:
  ```bash
  cd /opt/kuka_wms/opt/monitoring && docker compose up -d
  ```

---

### Giai đoạn 5: Kiểm tra nghiệm thu sau triển khai (Verification Gate)
- [ ] Gọi API Healthcheck: `curl -s http://localhost:8001/health` $\rightarrow$ Trả về `{"status":"healthy"}`.
- [ ] Kiểm tra kết nối Redis trong Backend log: `docker logs --tail 30 wms-backend` $\rightarrow$ Có dòng `Redis connected: ... (prefix=wms)`.
- [ ] Kiểm tra kết nối WebSocket Manager: Log có dòng `Websocket manager started`.
- [ ] Kiểm tra connection pool của Backend API: Đảm bảo biến môi trường `WMS_DB_ROLE=backend` được áp dụng (pool_size=20, max_overflow=20).
- [ ] Kiểm tra cả 3 Celery Worker đang hoạt động:
  ```bash
  docker exec -t wms-celery-logic celery -A app.core.celery_app.celery_app status
  ```
  Xác nhận 3 worker: `logic@...`, `status@...`, `fleet@...` đều phản hồi `OK`.
- [ ] Kiểm tra Celery Beat: Xác nhận task `production.scan_transport_queue` (mỗi 5s) và `production.sweep_fleet_tasks` (mỗi 15s) được trigger đều đặn trong log `wms-celery-beat`.
- [ ] Kiểm tra Prometheus scraping: Truy cập `http://localhost:9090/targets`, xác nhận các job `prometheus`, `wms-backend`, `postgres`, `redis` đều ở trạng thái `UP`.
- [ ] Kiểm tra Grafana Alloy & Loki:
  - `curl -s http://localhost:3100/ready` $\rightarrow$ Trả về `ready`.
  - Mở Grafana Dashboard `WMS Logs` trên cổng 3000, xác nhận log dạng structured metadata của backend và celery đang đổ về thời gian thực.
- [ ] Kiểm tra kết nối ngoại vi KUKA Fleet:
  - Máy chủ Linux gửi ping/curl thử nghiệm đến IP KUKA Fleet: `curl -s -I http://192.168.1.71:10870/interfaces/api` $\rightarrow$ Xác nhận thông tuyến mạng.
- [ ] Kiểm tra Frontend PDA:
  - Dùng PDA hoặc trình duyệt mở `http://<linux-ip>:5173`.
  - Đăng nhập tài khoản Quản đốc / Công nhân CNC.
  - Xác nhận trang tải mượt mà, không có lỗi `Network Error` hay `Mixed Content` trong F12 Console.

---

### Giai đoạn 6: Thiết lập vận hành tự động (Maintenance Setup)
- [ ] Cấu hình Systemd tự khởi động Docker khi reboot máy: `sudo systemctl enable docker`.
- [ ] Thiết lập Cron job dọn dẹp file log jsonl cũ hơn 3 ngày trong `backend/logs`.
- [ ] Thiết lập Cron job tự động backup CSDL PostgreSQL và Redis hằng ngày vào thư mục `/backup/wms/`.
- [ ] Lưu trữ tài liệu rollback khẩn cấp và bàn giao quyền truy cập máy chủ cho đội ngũ vận hành.
