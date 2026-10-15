import React from 'react';
import {
  ClearOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ApartmentOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import type { WashingSlot } from '@/types/pda';

interface WashingStationModalProps {
  slots: WashingSlot[];
  onReleaseSlot: (slotId: number) => void;
  onSimulateArrive?: (slotId: number) => void;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
}

export const WashingStationModal: React.FC<WashingStationModalProps> = ({
  slots,
  onReleaseSlot,
  onSimulateArrive,
  showToast,
}) => {
  // 1-Chạm giải phóng Slot về TRỐNG ngay lập tức
  const handleRelease = (slot: WashingSlot) => {
    if ('vibrate' in navigator) navigator.vibrate?.(60);

    const rackCode = slot.currentRack?.rackId || 'Rack';
    onReleaseSlot(slot.id);
    showToast(
      `Đã lấy đi rửa: Giải phóng [${slot.name}] (${rackCode}) thành công!`,
      'success'
    );
  };

  const occupiedCount = slots.filter((s) => s.status === 'OCCUPIED').length;

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Tiêu đề & Thống kê */}
      <div className="mb-3 flex items-center justify-between">
        <div>
          <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">
            Khu Vực Hậu Cần
          </span>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
            KHU TẨY RỬA (4 SLOTS)
          </h2>
        </div>
        <div className="text-right">
          <span className="text-[11px] bg-slate-800 text-slate-300 px-2 py-1 rounded-lg border border-slate-700 font-mono">
            {occupiedCount} / 4 Có Hàng
          </span>
        </div>
      </div>

      {/* Danh sách 4 Slot cố định */}
      <div className="flex flex-col gap-3 flex-1 overflow-y-auto pr-0.5">
        {slots.map((slot) => {
          const isEmpty = slot.status === 'EMPTY';
          const rack = slot.currentRack;

          return (
            <div
              key={slot.id}
              className={`rounded-2xl border p-3.5 transition-all shadow-sm ${
                isEmpty
                  ? 'bg-slate-800/40 border-slate-700/70 border-dashed'
                  : 'bg-slate-800/90 border-[#FF5800]/60 ring-1 ring-[#FF5800]/20'
              }`}
            >
              {/* Header Thẻ Slot */}
              <div className="flex items-center justify-between pb-2 border-b border-slate-700/60 mb-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-base font-black font-mono text-white">
                    {slot.name}
                  </span>
                </div>

                {isEmpty ? (
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-700/60 text-slate-400 border border-slate-600">
                    TRỐNG
                  </span>
                ) : (
                  <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-[#FF5800]/20 text-[#FF5800] border border-[#FF5800]/40 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-[#FF5800] animate-ping" />
                    CÓ RACK CHỜ RỬA
                  </span>
                )}
              </div>

              {/* Slot Đang Trống */}
              {isEmpty && (
                <div className="py-2 flex flex-col items-center justify-center text-center">
                  <InboxOutlined className="text-2xl text-slate-500 mb-1" />
                  <div className="text-xs text-slate-400 font-medium">
                    Vị trí sẵn sàng tiếp nhận hàng từ CNC
                  </div>
                  {/* Nút mô phỏng để test nhanh nhận rack từ CNC */}
                  {onSimulateArrive && (
                    <button
                      onClick={() => onSimulateArrive(slot.id)}
                      className="mt-2 text-[10px] text-slate-400 hover:text-slate-200 bg-slate-700/50 hover:bg-slate-700 px-2.5 py-1 rounded-lg border border-slate-600 active:scale-95 transition-all"
                    >
                      + Mô phỏng AMR đưa hàng vào
                    </button>
                  )}
                </div>
              )}

              {/* Slot Đã Có Hàng */}
              {!isEmpty && rack && (
                <div className="space-y-3">
                  {/* Chi tiết phôi / rack */}
                  <div className="bg-slate-900/80 rounded-xl p-2.5 border border-slate-700 space-y-1.5 text-xs">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Mã Rack:</span>
                      <span className="font-mono font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-600">
                        {rack.rackId}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-slate-400">Model chi tiết:</span>
                      <span className="font-bold text-[#FF5800]">{rack.model}</span>
                    </div>
                    <div className="flex justify-between items-center text-[11px] text-slate-400 pt-0.5 border-t border-slate-800">
                      <span className="flex items-center gap-1">
                        <ApartmentOutlined /> {rack.fromStation}
                      </span>
                      <span className="flex items-center gap-1">
                        <ClockCircleOutlined /> {rack.arrivedAt}
                      </span>
                    </div>
                  </div>

                  {/* Nút CỰC TO: BẤM UPDATE: ĐÃ LẤY ĐI RỬA */}
                  <button
                    onClick={() => handleRelease(slot)}
                    className="w-full min-h-[56px] bg-[#FF5800] hover:bg-[#e04e00] text-white rounded-xl font-black text-sm tracking-wide flex items-center justify-center gap-2 shadow-lg shadow-[#FF5800]/25 active:scale-[0.98] transition-all"
                  >
                    <ClearOutlined className="text-lg" />
                    <span>BẤM UPDATE: ĐÃ LẤY ĐI RỬA</span>
                  </button>
                  <p className="text-[10px] text-center text-slate-400">
                    ⚡ Chạm 1 lần để giải phóng slot về [TRỐNG] ngay lập tức
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
