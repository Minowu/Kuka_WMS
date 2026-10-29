"""Quản lý kết nối WebSocket thời gian thực, xác thực JWT tin nhắn đầu tiên và lắng nghe Redis Pub/Sub (Bước S4)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import db_session
from app.core.logger import get_logger
from app.core.security import decode_access_token
from app.modules.auth.auth_model import User
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.socket.event_bus import REDIS_EVENTS_CHANNEL

logger = get_logger("main")

# Mã đóng kết nối tiêu chuẩn khi xác thực thất bại hoặc hết hạn JWT token
WS_CLOSE_AUTH_FAILED = 4401

# Thời gian tối đa chờ tin nhắn xác thực đầu tiên từ client (giây)
AUTH_TIMEOUT_SECONDS = 5.0

# Thời gian tối đa chờ gửi 1 tin nhắn tới 1 PDA (tránh 1 PDA treo mạng làm chậm các PDA khác)
SEND_TIMEOUT_SECONDS = 2.0

# Chu kỳ gửi gói tin heartbeat giữ kết nối qua WiFi/Proxy (giây)
HEARTBEAT_INTERVAL_SECONDS = 30.0


class WebsocketManager:
    """
    Bộ quản lý kết nối WebSocket đa tiến trình (Multi-Process Safe):
    - Lưu ánh xạ `user_id -> set[WebSocket]` và tập hợp kết nối `admin_connections`.
    - Chạy vòng lặp nền `_redis_subscriber_loop()` lắng nghe kênh Redis Pub/Sub `wms:events`
      để nhận sự kiện từ cả FastAPI processes lẫn Celery workers (`wms-celery-fleet`, `wms-celery-logic`).
    - Chạy vòng lặp `_heartbeat_loop()` mỗi 30s để giữ kết nối, tự động đóng mã `4401` khi JWT hết hạn,
      và dọn dẹp ngay lập tức các socket đã mất kết nối.
    """

    def __init__(
        self,
        *,
        heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
        send_timeout: float = SEND_TIMEOUT_SECONDS,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.send_timeout = send_timeout

        self._heartbeat_task: Optional[asyncio.Task] = None
        self._subscriber_task: Optional[asyncio.Task] = None

        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        self.admin_connections: Set[WebSocket] = set()
        self.connection_meta: Dict[WebSocket, dict[str, Any]] = {}
        self.notification_by_warehouse: Dict[int, Set[WebSocket]] = {}

    async def start(self) -> None:
        """Khởi chạy cả 2 tác vụ nền: Heartbeat & Redis Pub/Sub Subscriber."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._redis_subscriber_loop())

    async def stop(self) -> None:
        """Dừng các tác vụ nền khi tắt ứng dụng FastAPI."""
        for task in (self._heartbeat_task, self._subscriber_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        self._heartbeat_task = None
        self._subscriber_task = None

    async def register_authenticated(
        self,
        websocket: WebSocket,
        *,
        user_id: int,
        username: str,
        is_admin: bool,
        exp: Optional[float] = None,
    ) -> None:
        """Đăng ký kết nối WebSocket sau khi đã xác thực JWT thành công."""
        self.active_connections.add(websocket)
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        if is_admin:
            self.admin_connections.add(websocket)

        self.connection_meta[websocket] = {
            "user_id": user_id,
            "username": username,
            "is_admin": is_admin,
            "exp": float(exp) if exp is not None else None,
        }

    async def connect(
        self,
        db: Session,
        websocket: WebSocket,
        warehouse_id: Optional[int] = None,
    ) -> None:
        """
        Kết nối kênh thông báo theo kho (giữ tương thích ngược).
        Kiểm tra sự tồn tại của Warehouse trong DB TRƯỚC KHI gọi `websocket.accept()`.
        """
        if warehouse_id is not None:
            warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if not warehouse:
                raise HTTPException(status_code=404, detail="Warehouse not found")

        await websocket.accept()
        self.active_connections.add(websocket)
        if warehouse_id is not None:
            if warehouse_id not in self.notification_by_warehouse:
                self.notification_by_warehouse[warehouse_id] = set()
            self.notification_by_warehouse[warehouse_id].add(websocket)
            logger.info("Connected to notification channel for warehouse %s", warehouse_id)

    async def disconnect(
        self,
        websocket: WebSocket,
        warehouse_id: Optional[int] = None,
    ) -> None:
        """Gỡ bỏ hoàn toàn kết nối WebSocket khỏi mọi danh sách theo dõi."""
        self.active_connections.discard(websocket)
        self.admin_connections.discard(websocket)

        meta = self.connection_meta.pop(websocket, None)
        if meta:
            uid = meta.get("user_id")
            if uid in self.user_connections:
                self.user_connections[uid].discard(websocket)
                if not self.user_connections[uid]:
                    del self.user_connections[uid]

        for uid in list(self.user_connections.keys()):
            if websocket in self.user_connections[uid]:
                self.user_connections[uid].discard(websocket)
                if not self.user_connections[uid]:
                    del self.user_connections[uid]

        if warehouse_id is not None and warehouse_id in self.notification_by_warehouse:
            self.notification_by_warehouse[warehouse_id].discard(websocket)
            if not self.notification_by_warehouse[warehouse_id]:
                del self.notification_by_warehouse[warehouse_id]

    async def _safe_send(self, websocket: WebSocket, message_text: str) -> bool:
        """
        Gửi tin nhắn văn bản tới 1 kết nối với giới hạn thời gian `send_timeout` (2 giây).
        Nếu gửi lỗi hoặc quá thời gian chờ, lập tức loại bỏ socket chết để không làm nghẽn vòng gửi.
        """
        try:
            await asyncio.wait_for(websocket.send_text(message_text), timeout=self.send_timeout)
            return True
        except Exception as exc:
            logger.debug("Removing dead/slow WebSocket connection on send failure: %s", exc)
            await self.disconnect(websocket)
            with contextlib.suppress(Exception):
                await websocket.close()
            return False

    async def _close_expired_socket(self, websocket: WebSocket) -> None:
        """Đóng kết nối với mã 4401 khi JWT token của phiên WebSocket đã hết hạn."""
        await self.disconnect(websocket)
        with contextlib.suppress(Exception):
            await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Token expired")

    async def _heartbeat_loop(self) -> None:
        """
        Vòng lặp định kỳ mỗi 30 giây:
        1. Kiểm tra thời hạn `exp` của JWT trên từng kết nối; nếu đã hết hạn -> đóng với mã `4401`.
        2. Gửi gói tin `heartbeat` với timeout 2s và dọn ngay các kết nối đã đứt mạng.
        """
        while True:
            await asyncio.sleep(self.heartbeat_interval)

            if not self.active_connections:
                continue

            now_ts = time.time()
            heartbeat_message = json.dumps(
                {
                    "type": "heartbeat",
                    "timestamp": now_ts,
                }
            )

            connections_snapshot = list(self.active_connections)
            send_coroutines = []
            for conn in connections_snapshot:
                meta = self.connection_meta.get(conn)
                exp = meta.get("exp") if meta else None
                if exp is not None and now_ts >= float(exp):
                    send_coroutines.append(self._close_expired_socket(conn))
                else:
                    send_coroutines.append(self._safe_send(conn, heartbeat_message))

            if send_coroutines:
                await asyncio.gather(*send_coroutines, return_exceptions=True)

    async def dispatch_envelope(self, envelope: dict[str, Any]) -> int:
        """
        Phân phối gói sự kiện nhận từ Redis Pub/Sub tới đúng tập hợp WebSocket của `user_ids` và `admins`.
        Trả về số lượng socket đã nhận tin nhắn thành công.
        """
        event_type = envelope.get("type")
        payload = envelope.get("payload") or {}
        targets = envelope.get("targets") or {}
        timestamp = envelope.get("timestamp")

        if not event_type:
            return 0

        target_user_ids = targets.get("user_ids") or []
        include_admins = bool(targets.get("admins", True))

        recipients: Set[WebSocket] = set()
        for raw_uid in target_user_ids:
            try:
                uid = int(raw_uid)
            except (TypeError, ValueError):
                continue
            sockets = self.user_connections.get(uid)
            if sockets:
                recipients.update(sockets)

        if include_admins and self.admin_connections:
            recipients.update(self.admin_connections)

        # floor.changed là sự kiện toàn phân xưởng -> luôn gửi cho toàn bộ kết nối đang mở
        if event_type == "floor.changed" or not target_user_ids:
            recipients.update(self.active_connections)

        if not recipients:
            return 0

        now_ts = time.time()
        valid_recipients: list[WebSocket] = []
        for ws in list(recipients):
            meta = self.connection_meta.get(ws)
            exp = meta.get("exp") if meta else None
            if exp is not None and now_ts >= float(exp):
                await self._close_expired_socket(ws)
            else:
                valid_recipients.append(ws)

        if not valid_recipients:
            return 0

        outbound_text = json.dumps(
            {
                "type": event_type,
                "payload": payload,
                "timestamp": timestamp,
            },
            default=str,
        )

        logger.info('[WS] Dispatching event "%s" to %s recipients: %s', event_type, len(valid_recipients), [self.connection_meta.get(w, {}).get("username") for w in valid_recipients])
        results = await asyncio.gather(
            *(self._safe_send(ws, outbound_text) for ws in valid_recipients),
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    async def _redis_subscriber_loop(self) -> None:
        """
        Vòng lặp nền lắng nghe kênh Redis Pub/Sub `wms:events` bằng `redis.asyncio`.
        Tự động kết nối lại nếu Redis khởi động lại.
        """
        while True:
            redis_client: Optional[aioredis.Redis] = None
            pubsub = None
            try:
                redis_client = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(REDIS_EVENTS_CHANNEL)
                logger.info("WebSocket Redis subscriber listening on channel '%s'", REDIS_EVENTS_CHANNEL)

                async for message in pubsub.listen():
                    if not isinstance(message, dict) or message.get("type") != "message":
                        continue
                    raw_data = message.get("data")
                    if not raw_data:
                        continue
                    try:
                        envelope = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                        if isinstance(envelope, dict):
                            await self.dispatch_envelope(envelope)
                    except Exception as parse_exc:
                        logger.warning("Failed to dispatch Redis WebSocket event: %s", parse_exc)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("WebSocket Redis subscriber connection error (retrying in 2s): %s", exc)
                await asyncio.sleep(2.0)
            finally:
                if pubsub is not None:
                    with contextlib.suppress(Exception):
                        await pubsub.unsubscribe(REDIS_EVENTS_CHANNEL)
                        await pubsub.close()
                if redis_client is not None:
                    with contextlib.suppress(Exception):
                        await redis_client.close()


ws_manager = WebsocketManager()
ws_router = APIRouter(tags=["WebSocket Realtime"])


def _authenticate_ws_token(token: str) -> Optional[dict[str, Any]]:
    """
    Giải mã `access_token` và kiểm tra tài khoản trong DB bằng một session cực ngắn.
    Trả về thông tin `{user_id, username, is_admin, exp}` nếu hợp lệ, ngược lại trả về `None`.
    """
    if not token or not isinstance(token, str):
        return None

    clean_token = token.strip()
    if clean_token.lower().startswith("bearer "):
        clean_token = clean_token[7:].strip()

    payload = decode_access_token(clean_token)
    if not payload:
        logger.warning("[WS] decode_access_token failed for token starting with: %s...", clean_token[:15] if len(clean_token) > 15 else clean_token)
        return None

    username = payload.get("sub")
    exp = payload.get("exp")
    if not username:
        return None

    if exp is not None and time.time() >= float(exp):
        return None

    with db_session() as db:
        user = (
            db.query(User)
            .options(selectinload(User.roles))
            .filter(User.username == str(username), User.is_active.is_(True))
            .first()
        )
        if not user:
            return None
        is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
        return {
            "user_id": user.id,
            "username": user.username,
            "is_admin": is_admin,
            "exp": float(exp) if exp is not None else None,
        }


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Endpoint `WEBSOCKET /api/v1/ws` dành cho PDA và giao diện giám sát:
    1. Sau khi bắt tay kết nối, client bắt buộc gửi tin nhắn đầu tiên:
       `{"type": "auth", "token": "<access_token>"}` trong vòng 5 giây.
    2. Nếu không gửi, token sai, hoặc tài khoản bị khóa -> đóng kết nối với mã `4401`.
    3. Trong suốt phiên kết nối, nếu thời điểm `exp` của token hết hạn -> đóng mã `4401`
       để trình duyệt tự động gọi refresh token và kết nối lại.
    """
    await websocket.accept()
    logger.info('[WS] Client connected from %s, awaiting auth token...', websocket.client)

    # Bước 1: Chờ tin nhắn xác thực đầu tiên trong vòng 5 giây
    try:
        raw_auth = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
        auth_msg = json.loads(raw_auth)
    except Exception:
        with contextlib.suppress(Exception):
            await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Authentication timeout or invalid JSON")
        return

    if not isinstance(auth_msg, dict) or auth_msg.get("type") != "auth":
        with contextlib.suppress(Exception):
            await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="First message must be auth")
        return

    token = str(auth_msg.get("token") or "").strip()
    user_info = _authenticate_ws_token(token)
    if not user_info:
        with contextlib.suppress(Exception):
            logger.warning("[WS] Auth FAILED: Invalid or expired token"); await websocket.close(code=WS_CLOSE_AUTH_FAILED, reason="Invalid or expired token")
        return

    await ws_manager.register_authenticated(
        websocket,
        user_id=user_info["user_id"],
        username=user_info["username"],
        is_admin=user_info["is_admin"],
        exp=user_info["exp"],
    )
    logger.info('[WS] Auth SUCCESS for user %s (id=%s, admin=%s). Total active: %s', user_info["username"], user_info["user_id"], user_info["is_admin"], len(ws_manager.active_connections))

    try:
        await asyncio.wait_for(
            websocket.send_text(
                json.dumps(
                    {
                        "type": "auth_ok",
                        "user_id": user_info["user_id"],
                        "username": user_info["username"],
                        "is_admin": user_info["is_admin"],
                    }
                )
            ),
            timeout=SEND_TIMEOUT_SECONDS,
        )

        # Bước 2: Duy trì kết nối và kiểm tra hạn token liên tục
        exp_ts = user_info.get("exp")
        while True:
            now_ts = time.time()
            if exp_ts is not None and now_ts >= float(exp_ts):
                await ws_manager._close_expired_socket(websocket)
                return

            # Tính thời gian chờ tiếp theo (không vượt quá thời điểm hết hạn token)
            wait_timeout = 35.0
            if exp_ts is not None:
                wait_timeout = max(0.05, min(wait_timeout, float(exp_ts) - now_ts))

            try:
                incoming_text = await asyncio.wait_for(websocket.receive_text(), timeout=wait_timeout)
            except asyncio.TimeoutError:
                # Hết khoảng chờ -> quay lại đầu vòng lặp để kiểm tra exp_ts
                continue

            with contextlib.suppress(Exception):
                msg_obj = json.loads(incoming_text)
                if isinstance(msg_obj, dict) and msg_obj.get("type") == "ping":
                    await ws_manager._safe_send(
                        websocket,
                        json.dumps({"type": "pong", "timestamp": time.time()}),
                    )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WebSocket session ended for user=%s: %s", user_info.get("username"), exc)
    finally:
        await ws_manager.disconnect(websocket)
