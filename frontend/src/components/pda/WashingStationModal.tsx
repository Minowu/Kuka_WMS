import React from 'react';
import type { WashingSlot } from '@/types/pda';

interface WashingStationModalProps {
  slots: WashingSlot[];
  onReleaseSlot: (slotId: number) => void;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
}

export const WashingStationModal: React.FC<WashingStationModalProps> = ({
  slots,
  onReleaseSlot,
  showToast,
}) => {
  const handleRelease = (slot: WashingSlot) => {
    if ('vibrate' in navigator) navigator.vibrate?.(60);

    const rackCode = slot.currentRack?.rackId || 'Rack';
    onReleaseSlot(slot.id);
    showToast(
      `Đã giải phóng ${slot.name} (${rackCode}) thành công!`,
      'success'
    );
  };

  const occupiedCount = slots.filter((s) => s.status === 'OCCUPIED').length;

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Header trạng thái */}
      <div className="mb-2.5 flex items-center justify-between">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          4 VỊ TRÍ TIẾP NHẬN
        </span>
        <span className="text-[11px] font-mono font-bold bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
          {occupiedCount} / 4 Có Hàng
        </span>
      </div>

      {/* 4 Slot cố định */}
      <div className="flex flex-col gap-2.5 flex-1 overflow-y-auto pr-0.5">
        {slots.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center my-auto bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="w-14 h-14 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-2xl mb-3 shadow-inner">
              🔒
            </div>
            <div className="text-white font-bold text-base mb-1.5">
              Chưa Được Phân Công Slot Tẩy Rửa
            </div>
            <div className="text-slate-400 text-xs leading-relaxed max-w-xs">
              Tài khoản của bạn chưa được gán vị trí ô đỗ nào tại Khu Tẩy Rửa. Vui lòng liên hệ Quản đốc xưởng để được phân quyền.
            </div>
          </div>
        ) : (
          slots.map((slot) => {
          const isOccupied = slot.status === 'OCCUPIED';
          const rack = slot.currentRack;

          return (
            <div
              key={slot.id}
              className={`rounded-xl border p-3 transition-all ${
                isOccupied
                  ? 'bg-slate-900 border-slate-700'
                  : 'bg-slate-900/60 border-slate-800/80'
              }`}
            >
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                <span className="text-sm font-bold font-mono text-white">
                  {slot.name}
                </span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                    isOccupied
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {isOccupied ? 'CÓ HÀNG' : 'TRỐNG'}
                </span>
              </div>

              {isOccupied && rack && (
                <div className="space-y-2">
                  <div className="bg-slate-950 p-2 rounded-lg border border-slate-800 space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Mã Rack:</span>
                      <span className="font-mono font-bold text-white">{rack.rackId}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Model:</span>
                      <span className="font-bold text-white truncate max-w-[200px]">{rack.model}</span>
                    </div>
                    <div className="flex justify-between text-[11px] text-slate-400 pt-0.5">
                      <span>Nguồn: {rack.fromStation}</span>
                      <span>Đến: {rack.arrivedAt}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleRelease(slot)}
                    className="w-full min-h-[48px] bg-[#10B981] hover:bg-[#059669] text-white rounded-xl font-bold text-xs tracking-wide active:scale-[0.98] transition-all cursor-pointer"
                  >
                    BÁO XONG: ĐÃ LẤY ĐI RỬA (GIẢI PHÓNG SLOT)
                  </button>
                </div>
              )}

              {!isOccupied && (
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] text-slate-500">
                    Slot trống • Sẵn sàng nhận xe từ CNC
                  </span>
                  
                </div>
              )}
            </div>
          );
        }))}
      </div>
    </div>
  );
};
