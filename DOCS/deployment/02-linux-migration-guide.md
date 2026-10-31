# Hướng Dẫn Di Chuyển Hệ Thống KUKA_WMS Sang Linux Server

Tài liệu này hướng dẫn chi tiết từng bước (step-by-step) quy trình chuyển giao và vận hành toàn bộ hệ sinh thái **KUKA_WMS** từ môi trường máy tính Windows sang máy chủ Linux chuyên dụng (Ubuntu Server 22.04 / 24.04 LTS hoặc Debian 12), đảm bảo dữ liệu toàn vẹn, bảo mật cao và vận hành ổn định 24/7.

---

## 1. Yêu Cầu Tiên Quyết (Prerequisites)

### 1.1. Cấu hình phần cứng máy chủ Linux đề xuất
- **CPU**: Tối thiểu 4 Cores (khuyến nghị 8 Cores để gánh 3 Celery worker prefork và monitoring stack).
- **RAM**: Tối thiểu 8 GB (khuyến nghị 16 GB).
- **Disk**: Tối thiểu 100 GB SSD/NVMe (PostgreSQL dữ liệu sản xuất + Loki logs + Prometheus TSDB 15 ngày).
- **Hệ điều hành**: Ubuntu Server 22.04 LTS / 24.04 LTS hoặc Debian 12 (64-bit).

### 1.2. Cài đặt Docker Engine & Docker Compose Plugin trên Linux
Không sử dụng `docker.io` cũ từ apt repository mặc định. Cài đặt Docker Engine chính thức từ Docker Inc:

```bash
# 1. Gỡ cài đặt các gói cũ (nếu có)
sudo apt-get remove -y docker docker-engine docker.io containerd runc

# 2. Cài đặt các gói phụ trợ
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release dos2unix postgresql-client-common redis-tools

# 3. Thêm GPG key chính thức của Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4. Thêm Docker Repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. Cài đặt Docker Engine và Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 6. Cấp quyền chạy docker không cần sudo cho user hiện tại
sudo usermod -aG docker $USER
newgrp docker

# 7. Kiểm tra phiên bản (Yêu cầu Docker 24+ và Compose v2.20+)
docker --version
docker compose version
```

---

## 2. Sao Chép Mã Nguồn & Xử Lý Định Dạng Ký Tự (CRLF to LF)

### 2.1. Đóng gói mã nguồn từ máy Windows
Trên máy tính Windows, mở PowerShell tại thư mục gốc dự án `D:\KuKA\KUKA_WMS`, tạo file nén loại trừ các thư mục rác và môi trường ảo:

```powershell
# Tạo file nén tar loại trừ .venv, node_modules, cache
tar --exclude="backend/.venv" `
    --exclude="frontend/node_modules" `
    --exclude="frontend/dist" `
    --exclude="backend/__pycache__" `
    --exclude="**/__pycache__" `
    --exclude=".pytest_cache" `
    --exclude=".ruff_cache" `
    --exclude="scratch" `
    --exclude="*.log" `
    --exclude="*.jsonl" `
    -czvf kuka_wms_source.tar.gz .
```

### 2.2. Chuyển file sang máy chủ Linux và giải nén
Dùng `scp` hoặc `rsync` chuyển file sang Linux Server:
```bash
# Trên máy Windows
scp kuka_wms_source.tar.gz user@192.168.1.50:/opt/

# Trên máy chủ Linux
sudo mkdir -p /opt/kuka_wms
sudo chown -R $USER:$USER /opt/kuka_wms
cd /opt/kuka_wms
tar -xzvf /opt/kuka_wms_source.tar.gz -C .
rm /opt/kuka_wms_source.tar.gz
```

### 2.3. Chuyển đổi định dạng ký tự kết thúc dòng (CRLF sang LF)
File tạo từ Windows có ký tự xuống dòng `\r\n` (CRLF) sẽ làm hỏng file cấu hình, script shell và entrypoint trên Linux:

```bash
cd /opt/kuka_wms

# Chuyển đổi toàn bộ file cấu hình, shell script, YAML sang định dạng LF
find . -type f \( -name "*.sh" -o -name "*.env*" -o -name "*.yml" -o -name "*.yaml" -o -name "*.alloy" -o -name "*.conf" \) -exec dos2unix {} +
```

---

## 3. Phân Quyền Thư Mục Trên Linux (Directory Permissions & UID)

Container `backend` ghi log dạng JSON Lines vào `/app/logs`, container `alloy` (chạy với user `alloy` UID `10001` hoặc `nobody`) đọc file log này từ thư mục bind mount `/var/log/wms`:

```bash
cd /opt/kuka_wms

# Tạo các thư mục lưu trữ dữ liệu nếu chưa có
mkdir -p backend/logs backend/uploads backend/app/static/file_import_item

# Cấp quyền đọc ghi cho container và user hệ thống
# Cấp quyền 777 hoặc phân quyền đọc cho UID 10001 (Alloy)
sudo chmod -R 777 backend/logs
sudo chmod -R 775 backend/uploads backend/app/static/file_import_item
```

---

## 4. Di Chuyển Dữ Liệu Sản Xuất (Data Migration)

> [!CAUTION]
> **PHÁT HIỆN ĐẶC BIỆT QUAN TRỌNG VỀ CSDL POSTGRESQL**:
> - Trên máy Windows hiện tại, container `wms-db` đang tồn tại **CẢ 2 CSDL**: `WMS_db` và `kuka`.
> - Kiểm tra thực tế:
>   - CSDL `WMS_db`: Chứa 27 bản ghi `item_stock`, nhưng bản ghi cập nhật cuối cùng là **19/10/2026**.
>   - CSDL `kuka`: Chứa 8 bản ghi `item_stock`, nhưng bản ghi cập nhật cuối cùng là **30/10/2026** (Chứa dữ liệu vận hành mới nhất do file `backend/.env` đang trỏ vào `/kuka`).
> - **Nguyên tắc xử lý**:
>   1. Backup cả 2 CSDL ra 2 file riêng biệt để lưu trữ tuyệt đối an toàn.
>   2. Chuẩn hóa tên CSDL đích trên Linux thành **`WMS_db`** theo đúng tiêu chuẩn dự án tại [`vault-docs/constraints.md`](file:///D:/KuKA/KUKA_WMS/vault-docs/constraints.md).
>   3. Khôi phục dữ liệu từ bản sao lưu mới nhất (từ database `kuka`) vào database đích `WMS_db` trên Linux.

### 4.1. Bước 1: Sao lưu PostgreSQL từ máy Windows
Thực hiện trên máy Windows (khi container `wms-db` đang chạy trên cổng 5433):

```powershell
# Chạy trực tiếp qua docker exec để đảm bảo phiên bản pg_dump khớp 100% với Postgres 16
docker exec -t wms-db pg_dump -U postgres -d kuka -F c -b -v -f /tmp/kuka_prod_active.dump
docker exec -t wms-db pg_dump -U postgres -d WMS_db -F c -b -v -f /tmp/wms_db_legacy.dump

# Copy file dump từ container ra máy host Windows
docker cp wms-db:/tmp/kuka_prod_active.dump D:\kuka_prod_active.dump
docker cp wms-db:/tmp/wms_db_legacy.dump D:\wms_db_legacy.dump

# Dọn dẹp file tạm trong container
docker exec -t wms-db rm /tmp/kuka_prod_active.dump /tmp/wms_db_legacy.dump
```

Chuyển 2 file dump sang Linux:
```bash
scp D:\kuka_prod_active.dump user@192.168.1.50:/opt/kuka_wms/
scp D:\wms_db_legacy.dump user@192.168.1.50:/opt/kuka_wms/
```

### 4.2. Bước 2: Sao lưu Redis AOF / RDB từ máy Windows
Redis lưu giữ trạng thái hàng đợi Celery và cache:

```powershell
# Bắt buộc Redis ghi dữ liệu bộ nhớ xuống đĩa
docker exec -t redis-wms redis-cli bgsave

# Copy thư mục dữ liệu Redis
docker cp redis-wms:/data/dump.rdb D:\redis_dump.rdb
# Nếu có file AOF (appendonly.aof)
docker cp redis-wms:/data/appendonlydir D:\redis_aof 2>$null
```

Chuyển sang Linux:
```bash
scp D:\redis_dump.rdb user@192.168.1.50:/opt/kuka_wms/
```

---

## 5. Thiết Lập Mạng Dùng Chung & Cấu Hình Môi Trường (.env)

### 5.1. Tạo mạng Docker dùng chung (External Bridge Network)
Để các container trong `docker-compose.yml` (Core) và `opt/monitoring/docker-compose.yml` (Monitoring) có thể giao tiếp với nhau bằng tên container qua DNS nội bộ của Docker:

```bash
docker network create wms-net
```

### 5.2. Chuẩn bị file `.env` chuẩn hóa cho Linux Production
Tạo file `/opt/kuka_wms/.env` (và sao chép vào `/opt/kuka_wms/backend/.env`):

```bash
cat << 'EOF' > /opt/kuka_wms/.env
APP_NAME="Warehouse Management System"
DEBUG=False

# Database config (Chuẩn hóa tên CSDL là WMS_db)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=ThadoProduction2026!Secure
POSTGRES_DB=WMS_db
DATABASE_URL=postgresql://postgres:ThadoProduction2026!Secure@db:5432/WMS_db

# Redis config
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_BROKER_RESULT_URL=redis://redis:6379/2

# KUKA Fleet Manager Integration
KUKA_BASE_URL=http://192.168.1.71:10870/interfaces/api
KUKA_ACCESS_TOKEN=1726185d4d777843ff5eb65171f11b12f9fb364ef2bd2d7c265e36e3389f18c1
KUKA_ORG_ID=TDS_KUKA_ORG

# Frontend API URL (Thay bằng IP thật của máy chủ Linux)
VITE_API_URL=http://192.168.1.50:8001

# Monitoring & Grafana
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=ThadoGrafana2026!
EOF

cp /opt/kuka_wms/.env /opt/kuka_wms/backend/.env
```

---

## 6. Khởi Chạy Hệ Thống & Khôi Phục Dữ Liệu Trên Linux

### 6.1. Khởi động CSDL PostgreSQL và Redis trước
Chỉ khởi động `db` và `redis` để chuẩn bị nạp dữ liệu:

```bash
cd /opt/kuka_wms
docker compose up -d db redis

# Chờ CSDL sẵn sàng (health check chuyển sang healthy)
docker compose ps db
```

### 6.2. Khôi phục dữ liệu vào CSDL `WMS_db`
Import file sao lưu mới nhất vào `WMS_db`:

```bash
# Nạp dữ liệu sản xuất từ file dump vào database WMS_db
docker exec -i wms-db pg_restore -U postgres -d WMS_db --clean --if-exists -v < /opt/kuka_wms/kuka_prod_active.dump

# Kiểm tra lại số lượng bảng và dữ liệu sau khi khôi phục
docker exec -t wms-db psql -U postgres -d WMS_db -c "SELECT count(*) FROM item_stock;"
docker exec -t wms-db psql -U postgres -d WMS_db -c "\dt"
```

### 6.3. Khôi phục dữ liệu Redis (Tùy chọn)
Nếu cần khôi phục cache và hàng đợi Celery:
```bash
docker compose stop redis
docker cp /opt/kuka_wms/redis_dump.rdb redis-wms:/data/dump.rdb
docker compose start redis
```

### 6.4. Khởi chạy toàn bộ hệ sinh thái KUKA_WMS
```bash
cd /opt/kuka_wms

# 1. Build và chạy toàn bộ dịch vụ WMS Core (Backend, Celery workers, Frontend)
docker compose build --no-cache
docker compose up -d

# 2. Khởi chạy Monitoring Stack
cd /opt/kuka_wms/opt/monitoring
docker compose up -d

# 3. Kiểm tra trạng thái toàn bộ containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## 7. Quy Trình Kiểm Tra & Nghiệm Thu (Post-Migration Verification)

Thực hiện lần lượt các lệnh kiểm tra sau trên máy chủ Linux:

```bash
# 1. Kiểm tra Backend API phản hồi HTTP 200
curl -s -i http://localhost:8001/health
# Kỳ vọng: HTTP/1.1 200 OK, {"status":"healthy"}

# 2. Kiểm tra Prometheus Metrics endpoint
curl -s http://localhost:8001/metrics | grep python_info
# Kỳ vọng: python_info{implementation="CPython",...} 1.0

# 3. Kiểm tra WebSocket Manager và Celery Beat
docker logs --tail 30 wms-backend
# Kỳ vọng: "Redis connected", "Websocket manager started"

# 4. Kiểm tra Celery Workers hoạt động và nhận đúng queue
docker exec -t wms-celery-logic celery -A app.core.celery_app.celery_app inspect active_queues
# Kỳ vọng: logic worker lắng nghe 'logic', status lắng nghe 'status', fleet lắng nghe 'fleet'

# 5. Kiểm tra Loki Server sẵn sàng nhận log
curl -s http://localhost:3100/ready
# Kỳ vọng: ready

# 6. Kiểm tra Grafana giao diện Web
curl -s -I http://localhost:3000/login
# Kỳ vọng: HTTP/1.1 200 OK

# 7. Kiểm tra Frontend React UI
curl -s -I http://localhost:5173
# Kỳ vọng: HTTP/1.1 200 OK (Nginx trả về index.html)
```

---

## 8. Cấu Hình Tường Lửa (UFW) & Bẫy Docker Iptables Bypass

> [!WARNING]
> **BẪY DOCKER IPTABLES BYPASS TRÊN LINUX**:
> Theo mặc định, Docker tự động thao tác trực tiếp với các iptables chain (`PREROUTING`, `DOCKER`) trước khi các rule của `ufw` được đánh giá. Nghĩa là dù bạn chạy `ufw default deny incoming`, các cổng đã map ra host trong Compose vẫn bị lộ ra ngoài!
>
> **Giải pháp bảo mật triệt để**:
> 1. Trong file `docker-compose.yml`, cổng PostgreSQL, Redis, Loki, Prometheus **bắt buộc phải bind vào `127.0.0.1`** (ví dụ: `127.0.0.1:5433:5432`). Khi bind vào localhost, Docker không mở cổng ra card mạng vật lý.
> 2. Cấu hình UFW kiểm soát các cổng công khai:

```bash
# Bật UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Mở cổng SSH quản trị
sudo ufw allow 22/tcp

# Mở cổng Frontend Web cho PDA và Quản đốc (5173)
sudo ufw allow 5173/tcp

# Mở cổng Backend API cho Webhook KUKA và PDA (8001)
sudo ufw allow 8001/tcp

# Chỉ mở cổng Grafana (3000) cho dải IP máy tính văn phòng/IT
# Ví dụ dải IP văn phòng là 192.168.1.0/24:
sudo ufw allow from 192.168.1.0/24 to any port 3000 proto tcp

# Áp dụng tường lửa
sudo ufw enable
sudo ufw status verbose
```

---

## 9. Vận Hành, Giới Hạn Dung Lượng Log & Sao Lưu Tự Động

### 9.1. Giới hạn dung lượng Log của Docker Daemon (Log Rotation)
Để ngăn chặn các container Docker ghi đầy phân vùng ổ cứng `/var/lib/docker/containers/`, cấu hình log rotation tập trung:

Tạo hoặc chỉnh sửa file `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```
Khởi động lại Docker daemon để áp dụng:
```bash
sudo systemctl restart docker
```

### 9.2. Tự động dọn dẹp file log ứng dụng (`backend/logs/*.jsonl`)
File log có cấu trúc được Alloy đọc và đẩy vào Loki. Cần cron job để nén và xóa các file log cũ trên đĩa:

Thêm cron job bằng lệnh `crontab -e`:
```cron
# Chạy lúc 02:00 sáng mỗi ngày: Nén file log cũ hơn 3 ngày, xóa file nén cũ hơn 15 ngày
0 2 * * * find /opt/kuka_wms/backend/logs -name "*.jsonl" -mtime +3 -exec gzip -f {} \;
0 3 * * * find /opt/kuka_wms/backend/logs -name "*.jsonl.gz" -mtime +15 -delete
```

### 9.3. Kịch bản sao lưu CSDL tự động hằng ngày (Automated Backup Script)
Tạo script sao lưu `/opt/kuka_wms/scripts/backup_wms.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backup/wms"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# 1. Backup PostgreSQL WMS_db
echo "[$DATE] Starting PostgreSQL backup..."
docker exec wms-db pg_dump -U postgres -d WMS_db -F c -b > "$BACKUP_DIR/wms_db_${DATE}.dump"

# 2. Backup Redis RDB
echo "[$DATE] Triggering Redis snapshot..."
docker exec redis-wms redis-cli bgsave
sleep 5
docker cp redis-wms:/data/dump.rdb "$BACKUP_DIR/redis_${DATE}.rdb"

# 3. Xóa các bản sao lưu cũ hơn 14 ngày
find "$BACKUP_DIR" -type f -mtime +14 -delete

echo "[$DATE] Backup completed successfully."
```

Cấp quyền thực thi và cấu hình Cron chạy hằng ngày lúc 01:00 AM:
```bash
chmod +x /opt/kuka_wms/scripts/backup_wms.sh

# Thêm vào crontab
(crontab -l 2>/dev/null; echo "0 1 * * * /opt/kuka_wms/scripts/backup_wms.sh >> /var/log/wms_backup.log 2>&1") | crontab -
```

---

## 10. Kế Hoạch Lùi Bước Khẩn Cấp (Rollback Plan)

Trong trường hợp triển khai trên Linux gặp sự cố nghiêm trọng không thể khắc phục trong vòng 30 phút (ví dụ: lỗi mạng xưởng không định tuyến được, đứt kết nối vật lý với KUKA Fleet):

### Quy trình Rollback về máy Windows cũ (< 10 phút):
1. **Dừng toàn bộ container trên Linux**:
   ```bash
   cd /opt/kuka_wms
   docker compose down
   cd /opt/kuka_wms/opt/monitoring && docker compose down
   ```
2. **Xuất dữ liệu phát sinh mới nhất từ Linux (nếu có)**:
   ```bash
   docker compose up -d db
   docker exec wms-db pg_dump -U postgres -d WMS_db -F c -b > /opt/kuka_wms/rollback_latest.dump
   docker compose down
   ```
3. **Kích hoạt lại hệ thống trên máy Windows**:
   - Khởi động lại các container trên Windows:
     ```powershell
     cd D:\KuKA\KUKA_WMS
     docker compose up -d db redis
     ```
   - (Nếu có dữ liệu mới từ Linux): Khôi phục file `rollback_latest.dump` vào CSDL trên Windows qua `docker exec -i wms-db pg_restore ...`.
   - Bật lại tiến trình FastAPI Backend trên Windows (cổng 8001).
   - Bật lại Vite Dev Server (cổng 5173).
4. **Kiểm tra thông luồng PDA**:
   - Mở màn hình PDA công nhân, bấm thử nghiệm lệnh gọi xe phôi để xác nhận hệ thống vận hành bình thường.
