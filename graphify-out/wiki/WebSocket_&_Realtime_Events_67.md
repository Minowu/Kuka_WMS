# WebSocket & Realtime Events (67)

> 26 nodes · cohesion 0.12

## Key Concepts

- **WebsocketManager** (14 connections) — `backend/app/socket/ws_manager.py`
- **._close_expired_socket()** (6 connections) — `backend/app/socket/ws_manager.py`
- **.dispatch_envelope()** (6 connections) — `backend/app/socket/ws_manager.py`
- **._safe_send()** (6 connections) — `backend/app/socket/ws_manager.py`
- **WebSocket** (6 connections)
- **.disconnect()** (5 connections) — `backend/app/socket/ws_manager.py`
- **._heartbeat_loop()** (5 connections) — `backend/app/socket/ws_manager.py`
- **.connect()** (4 connections) — `backend/app/socket/ws_manager.py`
- **._redis_subscriber_loop()** (4 connections) — `backend/app/socket/ws_manager.py`
- **.start()** (4 connections) — `backend/app/socket/ws_manager.py`
- **.register_authenticated()** (3 connections) — `backend/app/socket/ws_manager.py`
- **Any** (2 connections)
- **.stop()** (2 connections) — `backend/app/socket/ws_manager.py`
- **Session** (1 connections)
- **Kết nối kênh thông báo theo kho (giữ tương thích ngược). Kiểm tra sự tồn tại…** (1 connections) — `backend/app/socket/ws_manager.py`
- **Gỡ bỏ hoàn toàn kết nối WebSocket khỏi mọi danh sách theo dõi.** (1 connections) — `backend/app/socket/ws_manager.py`
- **Gửi tin nhắn văn bản tới 1 kết nối với giới hạn thời gian `send_timeout` (2…** (1 connections) — `backend/app/socket/ws_manager.py`
- **Đóng kết nối với mã 4401 khi JWT token của phiên WebSocket đã hết hạn.** (1 connections) — `backend/app/socket/ws_manager.py`
- **Vòng lặp định kỳ mỗi 30 giây: 1. Kiểm tra thời hạn `exp` của JWT trên từng kết…** (1 connections) — `backend/app/socket/ws_manager.py`
- **Phân phối gói sự kiện nhận từ Redis Pub/Sub tới đúng tập hợp WebSocket của…** (1 connections) — `backend/app/socket/ws_manager.py`
- **Vòng lặp nền lắng nghe kênh Redis Pub/Sub `wms:events` bằng `redis.asyncio`. Tự…** (1 connections) — `backend/app/socket/ws_manager.py`
- **Bộ quản lý kết nối WebSocket đa tiến trình (Multi-Process Safe): - Lưu ánh xạ…** (1 connections) — `backend/app/socket/ws_manager.py`
- **Khởi chạy cả 2 tác vụ nền: Heartbeat & Redis Pub/Sub Subscriber.** (1 connections) — `backend/app/socket/ws_manager.py`
- **Dừng các tác vụ nền khi tắt ứng dụng FastAPI.** (1 connections) — `backend/app/socket/ws_manager.py`
- **Đăng ký kết nối WebSocket sau khi đã xác thực JWT thành công.** (1 connections) — `backend/app/socket/ws_manager.py`
- *... and 1 more nodes in this community*

## Relationships

- [Production Dispatch & AMR Flow (5)](Production_Dispatch_&_AMR_Flow_5.md) (3 shared connections)
- [Warehouse Domain (64)](Warehouse_Domain_64.md) (1 shared connections)

## Source Files

- `backend/app/socket/ws_manager.py`

## Audit Trail

- EXTRACTED: 41 (98%)
- INFERRED: 1 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*