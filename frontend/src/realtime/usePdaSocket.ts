/**
 * Hook quản lý kết nối WebSocket thời gian thực cho PDA
 * Tự động xác thực JWT, bắt sự kiện floor.changed, fleet.task_failed,
 * hỗ trợ tự động gia hạn token khi gặp mã đóng 4401 và exponential backoff khi mất kết nối.
 */

import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/store/useAuthStore';
import { usePdaStore } from '@/store/usePdaStore';
import { refreshAccessTokenApi } from '@/api/authRefresh';
import { logger } from '@/logger';

function getWebSocketUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    const wsProto = envUrl.startsWith('https:') ? 'wss:' : 'ws:';
    const host = envUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
    return `${wsProto}//${host}/api/v1/ws`;
  }
  const isHttps = window.location.protocol === 'https:';
  return `${isHttps ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/ws`;
}

export function usePdaSocket(): void {
  const accessToken = useAuthStore((s) => s.access_token);
  const setToken = useAuthStore((s) => s.setToken);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  const fetchFloorState = usePdaStore((s) => s.fetchFloorState);
  const showToast = usePdaStore((s) => s.showToast);
  const setWsConnected = usePdaStore((s) => s.setWsConnected);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const debounceRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const backoffAttemptRef = useRef<number>(0);
  const seenMissionErrorsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!accessToken) {
      setWsConnected(false);
      return;
    }

    let isUnmounted = false;

    const triggerDebouncedFetch = () => {
      if (debounceRef.current) {
        window.clearTimeout(debounceRef.current);
      }
      // Debounce 300ms - 600ms với jitter ngẫu nhiên để tránh giật lag khi có nhiều sự kiện liên tiếp
      const jitterDelay = 300 + Math.floor(Math.random() * 300);
      debounceRef.current = window.setTimeout(() => {
        if (!isUnmounted) {
          fetchFloorState();
        }
      }, jitterDelay);
    };

    const scheduleReconnect = () => {
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      const attempt = backoffAttemptRef.current;
      const baseDelay = Math.min(1000 * Math.pow(2, attempt), 15000);
      const delay = baseDelay + Math.floor(Math.random() * 1000);
      backoffAttemptRef.current += 1;

      logger.info(`[WS] Lên lịch kết nối lại WebSocket lần ${backoffAttemptRef.current}`, {
        attempt: backoffAttemptRef.current,
        delay_ms: delay,
      });

      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (!isUnmounted) {
          connect();
        }
      }, delay);
    };

    const connect = () => {
      if (isUnmounted) return;

      const wsUrl = getWebSocketUrl();
      let ws: WebSocket;
      try {
        logger.info('[WS] Khởi tạo kết nối WebSocket...', { url: wsUrl });
        ws = new WebSocket(wsUrl);
      } catch (err) {
        logger.error('[WS] Lỗi khởi tạo WebSocket', { error: err ? String(err) : 'Init error' });
        console.warn('[WS] Lỗi khởi tạo WebSocket:', err);
        scheduleReconnect();
        return;
      }

      wsRef.current = ws;

      ws.onopen = () => {
        logger.info('[WS] Đã mở kết nối WebSocket thành công', { url: wsUrl });

        // Gửi thông điệp xác thực JWT đầu tiên
        const currentToken = useAuthStore.getState().access_token;
        if (currentToken && ws.readyState === WebSocket.OPEN) {
          const cleanToken = currentToken.replace(/^Bearer\s+/i, '').trim();
          console.log('[WS] Đã mở socket, gửi gói auth...');
          ws.send(JSON.stringify({ type: 'auth', token: cleanToken }));
        }

        // Khởi động chu kỳ gửi ping mỗi 25s để giữ kết nối qua các reverse proxy
        if (pingIntervalRef.current) {
          window.clearInterval(pingIntervalRef.current);
        }
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'auth_ok') {
            logger.info('[WS] Xác thực WebSocket thành công');
            setWsConnected(true);
            backoffAttemptRef.current = 0;
            // Tải trạng thái sàn ban đầu ngay sau khi xác thực thành công
            fetchFloorState();
            return;
          }

          if (msg.type === 'floor.changed') {
            triggerDebouncedFetch();
            return;
          }

          if (msg.type === 'fleet.task_failed') {
            const payload = msg.payload || {};
            const missionCode = payload.mission_code || 'unknown';

            // Khử trùng lặp thông báo lỗi trong vòng 10s
            if (!seenMissionErrorsRef.current.has(missionCode)) {
              seenMissionErrorsRef.current.add(missionCode);
              window.setTimeout(() => {
                seenMissionErrorsRef.current.delete(missionCode);
              }, 10000);

              const reason = payload.reason || payload.message || 'Lỗi điều xe AMR!';
              logger.warn(`[WS] Fleet task thất bại [${missionCode}]: ${reason}`, {
                mission_code: missionCode,
                reason,
              });
              showToast(`AMR [${missionCode}] thất bại: ${reason}`, 'error');
            }

            // Đồng thời làm mới lại sơ đồ sàn để giải phóng khoá / trạng thái vị trí
            triggerDebouncedFetch();
            return;
          }

          if (msg.type === 'pong') {
            // Heartbeat response
            return;
          }
        } catch (err) {
          logger.warn('[WS] Lỗi parse tin nhắn WebSocket', { error: String(err) });
          console.warn('[WS] Lỗi parse message:', err);
        }
      };

      ws.onclose = async (event) => {
        logger.warn(`[WS] Đóng kết nối WebSocket [code: ${event.code}]`, {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
        });

        setWsConnected(false);
        if (pingIntervalRef.current) {
          window.clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        if (isUnmounted) return;

        // Mã 4401: Token hết hạn -> Thử refresh token
        if (event.code === 4401) {
          logger.warn('[WS] Đóng kết nối do mã 4401 (Token hết hạn), đang làm mới token...', {
            code: event.code,
            reason: event.reason,
          });
          console.warn('[WS] Đóng kết nối do mã 4401 (Token hết hạn), đang làm mới token...');
          const currentRefresh = useAuthStore.getState().refresh_token;
          if (currentRefresh) {
            try {
              const res = await refreshAccessTokenApi(currentRefresh);
              setToken(res.access_token, res.refresh_token);
              logger.info('[WS] Làm mới token thành công sau mã 4401, đang kết nối lại...');
              // Thử kết nối lại ngay lập tức với token mới
              connect();
              return;
            } catch (refreshErr) {
              logger.error('[WS] Làm mới token thất bại sau mã 4401', { error: String(refreshErr) });
              console.error('[WS] Làm mới token thất bại:', refreshErr);
              clearAuth();
              return;
            }
          } else {
            logger.warn('[WS] Không tìm thấy refresh token sau mã 4401, đăng xuất');
            clearAuth();
            return;
          }
        }

        // Lỗi mạng hoặc server restart: exponential backoff (1s -> 2s -> 4s -> 8s -> tối đa 15s)
        scheduleReconnect();
      };

      ws.onerror = (err) => {
        logger.error('[WS] Lỗi kết nối WebSocket', { error: err ? String(err) : 'WebSocket error' });
        console.warn('[WS] Lỗi kết nối WebSocket:', err);
      };
    };

    // Bắt đầu kết nối
    connect();

    return () => {
      isUnmounted = true;
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
      }
      if (debounceRef.current) {
        window.clearTimeout(debounceRef.current);
      }
      if (pingIntervalRef.current) {
        window.clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        logger.info('[WS] Ngắt kết nối WebSocket (hook unmount)');
        wsRef.current.close();
        wsRef.current = null;
      }
      setWsConnected(false);
    };
  }, [accessToken, clearAuth, fetchFloorState, setToken, setWsConnected, showToast]);
}
