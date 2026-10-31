import React, { useEffect, useState, useRef, useCallback } from 'react';
import { getRawMaterialAndonQueueApi } from '@/api/andon';
import type { AndonRawMaterialDemand, AndonRawSlotStatus } from '@/types/andon';
import { useAuthStore } from '@/store/useAuthStore';
import {
  FullscreenOutlined,
  FullscreenExitOutlined,
  ReloadOutlined,
  CheckCircleFilled,
  WarningFilled,
  InboxOutlined,
} from '@ant-design/icons';

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

export default function RawMaterialAndonPage() {
  const accessToken = useAuthStore((s) => s.access_token);

  const [demands, setDemands] = useState<AndonRawMaterialDemand[]>([]);
  const [rawSlots, setRawSlots] = useState<AndonRawSlotStatus[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);

  // Fetch data
  const loadData = useCallback(async () => {
    try {
      const res = await getRawMaterialAndonQueueApi();
      setDemands(res.demands || []);
      setRawSlots(res.rawSlots || []);
    } catch (err) {
      console.error('[Andon] Failed to fetch raw material queue:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and 3s polling fallback (works for both public and logged-in displays)
  useEffect(() => {
    loadData();
    const pollInterval = window.setInterval(loadData, 3000);
    return () => window.clearInterval(pollInterval);
  }, [loadData]);

  // Realtime WebSocket for instant event-driven refresh
  useEffect(() => {
    if (!accessToken) return;

    let isUnmounted = false;

    const connectWs = () => {
      try {
        const wsUrl = getWebSocketUrl();
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify({ type: 'auth', token: accessToken }));
        };

        ws.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data);
            if (data.type === 'auth_ok') {
              if (!isUnmounted) setIsWsConnected(true);
              loadData();
            } else if (data.type === 'floor.changed' || data.type === 'production.queue_updated') {
              loadData();
            }
          } catch {
            // Ignore malformed WS message
          }
        };

        ws.onclose = () => {
          if (!isUnmounted) {
            setIsWsConnected(false);
            reconnectTimerRef.current = window.setTimeout(connectWs, 5000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (err) {
        if (!isUnmounted) {
          reconnectTimerRef.current = window.setTimeout(connectWs, 5000);
        }
      }
    };

    connectWs();

    return () => {
      isUnmounted = true;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [accessToken, loadData]);

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
      }
    }
  };

  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', handleFsChange);
    return () => document.removeEventListener('fullscreenchange', handleFsChange);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col p-4 md:p-6 select-none font-sans overflow-x-hidden">
      {/* ── TOP HEADER (Optimized for 50-65" TV) ── */}
      <header className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
        {/* Left: Title & Area */}
        <div className="flex items-center gap-4">
          <div className="h-12 w-3 bg-amber-500 rounded-full shadow-[0_0_15px_rgba(245,158,11,0.5)]" />
          <div>
            <h1 className="text-3xl md:text-4xl font-extrabold tracking-wide text-white uppercase drop-shadow-md">
              BẢNG ĐIỀU ĐỘ CẤP PHÔI NGUYÊN LIỆU
            </h1>
          </div>
        </div>

        {/* Center: Live Connection Badge */}
        <div className="flex items-center gap-4">
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs md:text-sm font-semibold tracking-wide ${
              isWsConnected
                ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-400'
                : 'bg-cyan-950/60 border-cyan-500/50 text-cyan-400'
            }`}
          >
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                isWsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-cyan-400 animate-pulse'
              }`}
            />
            {isWsConnected ? 'REALTIME ACTIVE' : 'TỰ ĐỘNG CẬP NHẬT (3S)'}
          </div>
        </div>

        {/* Right: Fullscreen */}
        <div className="flex items-center gap-4">
          <button
            onClick={toggleFullscreen}
            className="p-3 bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-200 hover:text-white rounded-xl transition border border-slate-700 text-lg flex items-center justify-center cursor-pointer shadow-md"
            title={isFullscreen ? 'Thu nhỏ' : 'Toàn màn hình TV'}
          >
            {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          </button>
        </div>
      </header>

      {/* ── MAIN DEMANDS TABLE (TV 65-70% height) ── */}
      <section className="flex-1 flex flex-col mb-4 bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-2xl backdrop-blur-sm overflow-hidden">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-wide">
              DANH SÁCH MÁY CNC ĐANG CHỜ CẤP PHÔI
            </h2>
            <span
              className={`px-3 py-1 rounded-full text-base font-extrabold font-mono shadow-sm ${
                demands.length > 0
                  ? 'bg-rose-950/80 border border-rose-500/60 text-rose-300 animate-pulse'
                  : 'bg-emerald-950/60 border border-emerald-500/50 text-emerald-300'
              }`}
            >
              {demands.length > 0 ? `ĐANG CHỜ: ${demands.length} MÁY` : '0 YÊU CẦU CHỜ'}
            </span>
          </div>
        </div>

        {/* Table / Empty State */}
        <div className="flex-1 flex flex-col overflow-y-auto">
          {demands.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center py-12 text-center">
              <div className="w-24 h-24 rounded-full bg-emerald-950/50 border border-emerald-500/30 flex items-center justify-center text-5xl text-emerald-400 mb-5 shadow-[0_0_30px_rgba(16,185,129,0.2)]">
                <CheckCircleFilled />
              </div>
              <h3 className="text-3xl font-extrabold text-emerald-400 tracking-wide mb-2">
                TẤT CẢ MÁY CNC ĐÃ ĐẦY ĐỦ PHÔI
              </h3>
              <p className="text-slate-400 text-lg max-w-md">
                Hiện tại không có máy CNC nào đang xếp hàng đợi cấp phôi nguyên liệu thô.
              </p>
            </div>
          ) : (
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b-2 border-slate-700 bg-slate-900 text-slate-300 text-lg md:text-xl font-bold tracking-wider uppercase">
                    <th className="py-4 px-4 text-center w-20">STT</th>
                    <th className="py-4 px-6 w-72">Mã Phôi / Model</th>
                    <th className="py-4 px-6">Tên Chi Tiết Sản Phẩm</th>
                    <th className="py-4 px-6 w-80">Máy CNC Yêu Cầu</th>
                    <th className="py-4 px-6 text-center w-60">Thời Điểm Bấm Gọi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-200">
                  {demands.map((item, idx) => (
                    <tr
                      key={item.id}
                      className={`hover:bg-slate-800/60 transition-colors ${
                        idx === 0
                          ? 'bg-amber-950/20 border-l-4 border-l-amber-500'
                          : idx % 2 === 0
                          ? 'bg-slate-900/40'
                          : 'bg-transparent'
                      }`}
                    >
                      {/* STT */}
                      <td className="py-5 px-4 text-center font-mono text-2xl font-bold text-slate-400">
                        {idx + 1}
                      </td>

                      {/* Model Code */}
                      <td className="py-5 px-6">
                        <div className="font-mono text-3xl md:text-4xl font-extrabold text-amber-400 tracking-wider drop-shadow-sm">
                          {item.modelCode}
                        </div>
                      </td>

                      {/* Model Name */}
                      <td className="py-5 px-6">
                        <div className="text-xl md:text-2xl font-semibold text-white">
                          {item.modelName}
                        </div>
                        <div className="text-xs text-slate-400 font-mono mt-0.5">
                          Lệnh: {item.requestCode}
                        </div>
                      </td>

                      {/* Machine CNC & Slot (P1/P2) */}
                      <td className="py-5 px-6">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-2xl md:text-3xl font-extrabold text-cyan-400 tracking-wide">
                            {item.machineCode}
                          </span>
                          {item.positionIndex !== null && item.positionIndex !== undefined && (
                            <span className="px-3 py-1 rounded-lg bg-cyan-950/80 border border-cyan-500/50 text-cyan-300 font-mono text-lg font-bold">
                              P{item.positionIndex}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-slate-400 mt-1">
                          {item.machineName}
                        </div>
                      </td>

                      {/* Static Call Time (HH:mm:ss) */}
                      <td className="py-5 px-6 text-center">
                        <div className="inline-block px-4 py-2 rounded-xl bg-slate-950 border border-slate-700 font-mono text-2xl md:text-3xl font-extrabold text-slate-100 shadow-inner">
                          {item.calledAt || '--:--:--'}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      {/* ── BOTTOM SECTION: 7 RAW MATERIAL SLOTS (RAW-01 .. RAW-07) ── */}
      <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 shadow-xl">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
          <div className="flex items-center gap-3">
            <h3 className="text-xl md:text-2xl font-bold text-white tracking-wide uppercase align-middle">
              TÌNH TRẠNG 7 VỊ TRÍ CẤP PHÔI
            </h3>
          </div>

          <div className="flex items-center gap-4 text-xs md:text-sm font-semibold">
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded bg-emerald-500 border border-emerald-400" />
              <span className="text-emerald-400">Ô TRỐNG (Cần nạp xe phôi)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3.5 h-3.5 rounded bg-slate-700 border border-slate-600" />
              <span className="text-slate-300">ĐÃ CÓ XE PHÔI</span>
            </div>
          </div>
        </div>

        {/* 7 Columns Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {rawSlots.map((slot) => {
            const isEmpty = !slot.hasCart;
            return (
              <div
                key={slot.locationId}
                className={`flex flex-col justify-between p-3.5 rounded-xl border-2 transition-all shadow-md min-h-[140px] ${
                  isEmpty
                    ? 'border-emerald-500/60 bg-emerald-950/25 hover:border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                    : 'border-slate-700 bg-slate-950/70 hover:border-slate-600'
                }`}
              >
                {/* Header: Location Code */}
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5 mb-2">
                  <span className="font-mono text-xl font-extrabold text-white tracking-wider">
                    {slot.locationCode}
                  </span>
                  {isEmpty ? (
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-900/60 border border-emerald-500/40 text-emerald-300">
                      TRỐNG
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-xs font-bold bg-slate-800 border border-slate-700 text-slate-400">
                      CÓ XE
                    </span>
                  )}
                </div>

                {/* Content Details */}
                <div className="flex-1 flex flex-col justify-center">
                  {isEmpty ? (
                    <div className="text-center py-2">
                      <div className="text-emerald-400 font-extrabold text-lg tracking-wide uppercase">
                        SẴN SÀNG
                      </div>
                      <div className="text-xs text-emerald-500/80 font-medium">
                        Có thể xếp xe mới
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-1">
                      <div className="font-mono text-2xl font-black text-amber-400 truncate tracking-wide">
                        {slot.modelCode || 'N/A'}
                      </div>
                      <div className="text-xs font-semibold text-slate-300 truncate">
                        {slot.modelName || 'Chưa định danh'}
                      </div>
                      <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5 mt-0.5">
                        <span className="text-slate-500">Mã xe:</span>
                        <span className="text-slate-200 font-bold">{slot.cartCode || 'Chưa gắn'}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer slot index indicator */}
                <div className="text-[10px] text-slate-500 font-mono text-right mt-1 pt-1 border-t border-slate-800/60">
                  {slot.name}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
