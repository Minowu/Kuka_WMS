import React from 'react';
import type { CncMachineStation, PartModel } from '@/types/pda';

interface CncLineModalProps {
  stations: CncMachineStation[];
  models?: PartModel[];
  onCallMaterial: (stationId: string) => void;
  onUpdateLevel: (stationId: string) => void;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
}

export const CncLineModal: React.FC<CncLineModalProps> = ({
  stations,
  onCallMaterial,
  onUpdateLevel,
  showToast: _showToast,
}) => {

  const getLevelLabel = (level: number) => {
    switch (level) {
      case 0:
        return 'Level 0: Phôi Thô';
      case 1:
        return 'Level 1: Phay Thô';
      case 2:
        return 'Level 2: Phay Tinh';
      case 3:
        return 'Level 3: Hoàn Tất CNC';
      default:
        return `Level ${level}`;
    }
  };

  const renderPosBadge = (pos?: number) => {
    if (!pos) return null;
    switch (pos) {
      case 1:
        return (
          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-blue-900/80 text-blue-300 border border-blue-600/60 shadow-xs">
            P1
          </span>
        );
      case 2:
        return (
          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-purple-900/80 text-purple-300 border border-purple-600/60 shadow-xs">
            P2
          </span>
        );
      case 3:
        return (
          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-900/80 text-amber-300 border border-amber-600/60 shadow-xs">
            P3
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            P{pos}
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Danh sách trạm CNC */}
      <div className="flex flex-col gap-3 flex-1 overflow-y-auto pr-0.5">
        {stations.map((st) => {
          const isEmpty = st.status === 'EMPTY';
          const isCalling = st.status === 'CALLING';
          const isOccupied = st.status === 'OCCUPIED';
          const rack = st.currentRack;
          const isFinalStep = st.assignedStageLevel >= 3;

          return (
            <div
              key={st.id}
              className={`rounded-xl border p-3 transition-all ${
                isEmpty
                  ? 'bg-slate-900/90 border-slate-800'
                  : isCalling
                  ? 'bg-amber-950/20 border-amber-600/50'
                  : 'bg-slate-900 border-slate-700'
              }`}
            >
              {/* Header trạm */}
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-base font-bold font-mono text-white">
                    {st.name}
                  </span>
                  {renderPosBadge(st.positionIndex)}
                  <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Level {st.assignedStageLevel}: {st.stageName}
                  </span>
                </div>

                {isEmpty && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    TRỐNG
                  </span>
                )}
                {isCalling && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    AMR ĐANG TỚI
                  </span>
                )}
                {isOccupied && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    ĐANG GIA CÔNG
                  </span>
                )}
              </div>

              {/* 1. TRẠNG THÁI: TRỐNG -> GỌI PHÔI */}
              {isEmpty && (
                <div className="space-y-2">
                  <div className="text-[11px] text-slate-400">
                    Đầu vào yêu cầu:{' '}
                    <span className="text-slate-200 font-bold font-mono">
                      {(st.assignedStageLevel ?? 1) <= 1 ? 'Level 0 (Phôi thô)' : `Level ${(st.assignedStageLevel ?? 1) - 1}`}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      if ('vibrate' in navigator) navigator.vibrate?.(40);
                      onCallMaterial(st.id);
                    }}
                    className="w-full min-h-[50px] bg-[#3B82F6] hover:bg-blue-600 text-white rounded-xl font-bold text-sm tracking-wide active:scale-[0.98] transition-all cursor-pointer shadow-md"
                  >
                    GỌI PHÔI (ĐIỀU AMR ĐẾN)
                  </button>
                </div>
              )}

              {/* 2. TRẠNG THÁI: AMR ĐANG TỚI */}
              {isCalling && (
                <div className="space-y-2.5">
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
                    <div className="text-slate-400">Model yêu cầu:</div>
                    <div className="font-bold text-white mt-0.5">
                      {st.callingModel || 'Phôi tiêu chuẩn'}
                    </div>
                  </div>
                  <div className="w-full min-h-[46px] bg-amber-500/10 border border-amber-500/30 text-amber-300 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 px-3 py-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                    <span>AMR đang vận chuyển phôi đến trạm...</span>
                  </div>
                </div>
              )}

              {/* 3. TRẠNG THÁI: ĐÃ CÓ HÀNG -> BÁO XONG CẬP NHẬT LEVEL CHỈ ĐỊNH */}
              {isOccupied && rack && (
                <div className="space-y-2.5">
                  <div className="bg-slate-950 rounded-lg p-2.5 border border-slate-800 space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Mã Rack:</span>
                      <span className="font-mono font-bold text-white">{rack.rackId}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Model:</span>
                      <span className="font-bold text-white truncate max-w-[200px]">{rack.model}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-slate-800 text-[11px]">
                      <span className="text-slate-400">Hiện tại: {getLevelLabel(rack.level)}</span>
                      <span className="text-[#FF5800] font-bold font-mono">
                        Đích: Level {st.assignedStageLevel}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      if ('vibrate' in navigator) navigator.vibrate?.(60);
                      onUpdateLevel(st.id);
                    }}
                    className={`w-full min-h-[54px] text-white rounded-xl font-bold text-sm tracking-wide active:scale-[0.98] transition-all cursor-pointer ${
                      isFinalStep
                        ? 'bg-[#FF5800] hover:bg-[#e04e00]'
                        : 'bg-[#10B981] hover:bg-[#059669]'
                    }`}
                  >
                    {isFinalStep
                      ? `BÁO XONG: CẬP NHẬT LEVEL ${st.assignedStageLevel} (CHUYỂN TẨY RỬA)`
                      : `BÁO XONG: CẬP NHẬT LEVEL ${st.assignedStageLevel}`}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
