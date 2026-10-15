import React, { useState } from 'react';
import {
  RocketOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CarOutlined,
  CloseOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { CncMachineStation, PartModel } from '@/types/pda';

interface CncLineModalProps {
  stations: CncMachineStation[];
  models: PartModel[];
  onCallMaterial: (stationId: string, modelId: string) => void;
  onUpdateLevel: (stationId: string) => void;
  onFastArrive?: (stationId: string) => void;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
}

export const CncLineModal: React.FC<CncLineModalProps> = ({
  stations,
  models,
  onCallMaterial,
  onUpdateLevel,
  onFastArrive,
  showToast,
}) => {
  // Trạng thái mở Sheet chọn Model cho máy nào
  const [callingForStationId, setCallingForStationId] = useState<string | null>(null);

  // 1-Chạm Chọn Model để gọi hàng ngay lập tức
  const handleSelectModelAndCall = (modelId: string) => {
    if (!callingForStationId) return;
    if ('vibrate' in navigator) navigator.vibrate?.(40);

    const targetStation = callingForStationId;
    setCallingForStationId(null); // Đóng sheet ngay
    onCallMaterial(targetStation, modelId);
  };

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

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Tiêu đề khu vực */}
      <div className="mb-3 flex items-center justify-between">
        <div>
          <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">
            Quản Lý Trạm Máy
          </span>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[#3B82F6]" />
            KHU VỰC MÁY CNC ({stations.length} TRẠM)
          </h2>
        </div>
        <div className="text-right">
          <span className="text-[11px] bg-slate-800 text-slate-300 px-2 py-1 rounded-lg border border-slate-700 font-mono">
            {stations.length} Vị trí
          </span>
        </div>
      </div>

      {/* Danh sách các trạm máy CNC */}
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
              className={`rounded-2xl border p-3.5 transition-all shadow-sm ${
                isEmpty
                  ? 'bg-slate-800/80 border-slate-700'
                  : isCalling
                  ? 'bg-amber-950/20 border-amber-500/50'
                  : 'bg-slate-800/90 border-[#10B981]/50'
              }`}
            >
              {/* Header của thẻ trạm CNC */}
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-700/60 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-lg font-black font-mono text-white tracking-wide">
                    {st.name}
                  </span>
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 font-mono">
                    Level {st.assignedStageLevel}: {st.stageName}
                  </span>
                </div>

                {/* Badge trạng thái */}
                {isEmpty && (
                  <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-slate-700/80 text-slate-300 border border-slate-600">
                    TRỐNG
                  </span>
                )}
                {isCalling && (
                  <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 animate-pulse">
                    <CarOutlined className="animate-bounce" />
                    AMR ĐANG ĐẾN
                  </span>
                )}
                {isOccupied && (
                  <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                    ĐANG GIA CÔNG
                  </span>
                )}
              </div>

              {/* Nội dung tương ứng theo trạng thái */}

              {/* 1. TRẠNG THÁI: TRỐNG -> NÚT TO GỌI HÀNG */}
              {isEmpty && (
                <div className="space-y-3">
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    <InfoCircleOutlined className="text-slate-500" />
                    <span>
                      Trạm máy đang trống, cần phôi đầu vào{' '}
                      <strong className="text-blue-300">
                        {st.assignedStageLevel === 1 ? 'Level 0 (Phôi thô)' : `Level ${st.assignedStageLevel - 1}`}
                      </strong>
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      if ('vibrate' in navigator) navigator.vibrate?.(30);
                      setCallingForStationId(st.id);
                    }}
                    className="w-full min-h-[54px] bg-[#3B82F6] hover:bg-[#2563eb] text-white rounded-xl font-black text-sm tracking-wide flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 active:scale-[0.98] transition-all"
                  >
                    <RocketOutlined className="text-lg" />
                    <span>GỌI HÀNG (ĐIỀU AMR ĐẾN)</span>
                  </button>
                </div>
              )}

              {/* 2. TRẠNG THÁI: AMR ĐANG ĐIỀU TỚI */}
              {isCalling && (
                <div className="space-y-3">
                  <div className="bg-amber-500/10 rounded-xl p-2.5 border border-amber-500/30 flex items-center justify-between">
                    <div>
                      <div className="text-[11px] text-amber-400 font-medium">Model yêu cầu:</div>
                      <div className="text-sm font-bold text-white">
                        {st.callingModel || 'Phôi tiêu chuẩn'}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        Chuẩn bị nhận xe: Level {st.assignedStageLevel === 1 ? 0 : st.assignedStageLevel - 1}
                      </div>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-300 animate-spin">
                      <SyncOutlined />
                    </div>
                  </div>

                  {/* Nút mô phỏng AMR đến để test tức thì 1 chạm */}
                  <button
                    onClick={() => onFastArrive?.(st.id)}
                    className="w-full min-h-[52px] bg-amber-500 hover:bg-amber-600 text-slate-950 font-black text-xs rounded-xl flex items-center justify-center gap-2 active:scale-[0.98] transition-all"
                  >
                    <CarOutlined className="text-base" />
                    <span>MÔ PHỎNG: AMR ĐÃ CẬP BẾN</span>
                  </button>
                </div>
              )}

              {/* 3. TRẠNG THÁI: ĐÃ CÓ HÀNG -> BÁO XONG UPDATE LEVEL ĐƯỢC CHỈ ĐỊNH */}
              {isOccupied && rack && (
                <div className="space-y-3">
                  {/* Thẻ chi tiết Rack & Model */}
                  <div className="bg-slate-900/80 rounded-xl p-2.5 border border-slate-700/80 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400">Mã Rack:</span>
                      <span className="font-mono font-bold text-[#3B82F6] bg-blue-950/50 px-2 py-0.5 rounded border border-blue-500/30">
                        {rack.rackId}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400">Model chi tiết:</span>
                      <span className="font-bold text-white truncate max-w-[200px]">
                        {rack.model}
                      </span>
                    </div>

                    {/* Hiển thị rõ Level hiện tại của phôi vs Level đích máy này sẽ update */}
                    <div className="pt-1">
                      <div className="flex justify-between text-[11px] font-bold text-slate-400 mb-1">
                        <span>Đầu vào: <span className="text-amber-300">{getLevelLabel(rack.level)}</span></span>
                        <span>Đích: <span className="text-emerald-400">Level {st.assignedStageLevel} ({st.stageName})</span></span>
                      </div>
                      <div className="grid grid-cols-3 gap-1.5 h-2 rounded-full overflow-hidden bg-slate-800">
                        <div
                          className={`h-full rounded-full ${
                            rack.level >= 1 ? 'bg-emerald-500' : 'bg-slate-700'
                          }`}
                        />
                        <div
                          className={`h-full rounded-full ${
                            rack.level >= 2 ? 'bg-emerald-500' : 'bg-slate-700'
                          }`}
                        />
                        <div
                          className={`h-full rounded-full ${
                            rack.level >= 3 ? 'bg-emerald-500' : 'bg-slate-700'
                          }`}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Nút CỰC TO Báo Xong -> Cập nhật bằng đúng Level được chỉ định */}
                  <button
                    onClick={() => {
                      if ('vibrate' in navigator) navigator.vibrate?.(60);
                      onUpdateLevel(st.id);
                    }}
                    className={`w-full min-h-[56px] text-white rounded-xl font-black text-sm tracking-wide flex items-center justify-center gap-2 shadow-lg active:scale-[0.98] transition-all ${
                      isFinalStep
                        ? 'bg-[#FF5800] hover:bg-[#e04e00] shadow-orange-500/25'
                        : 'bg-[#10B981] hover:bg-[#059669] shadow-emerald-500/25'
                    }`}
                  >
                    <CheckCircleOutlined className="text-xl" />
                    <span>
                      {isFinalStep
                        ? `BÁO XONG: CẬP NHẬT LEVEL ${st.assignedStageLevel} -> CHUYỂN TẨY RỬA`
                        : `BÁO XONG -> CẬP NHẬT LEVEL ${st.assignedStageLevel} (${st.stageName})`}
                    </span>
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ================= BOTTOM SHEET / MODAL CHỌN MODEL GỌI HÀNG ================= */}
      {callingForStationId && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end bg-black/80 backdrop-blur-xs p-3">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-4 shadow-2xl max-w-[480px] w-full mx-auto max-h-[85vh] flex flex-col animate-in fade-in slide-in-from-bottom duration-150">
            {/* Header Sheet */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <span className="text-[11px] text-[#3B82F6] font-bold uppercase tracking-wider">
                  GỌI HÀNG ĐẾN {callingForStationId}
                </span>
                <h3 className="text-base font-black text-white">Chạm Chọn Model Cần Cấp:</h3>
              </div>
              <button
                onClick={() => setCallingForStationId(null)}
                className="w-9 h-9 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center justify-center active:scale-90"
              >
                <CloseOutlined />
              </button>
            </div>

            {/* Danh sách Model - 1 chạm gửi lệnh ngay */}
            <div className="flex flex-col gap-2.5 my-3 overflow-y-auto pr-1">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleSelectModelAndCall(model.id)}
                  className="min-h-[52px] p-3 rounded-xl bg-slate-800 hover:bg-[#3B82F6] border border-slate-700 hover:border-blue-400 text-left flex items-center justify-between group transition-all active:scale-[0.98]"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-lg bg-slate-700 group-hover:bg-white/20 text-white flex items-center justify-center font-bold text-xs font-mono">
                      {model.code}
                    </span>
                    <div>
                      <div className="font-bold text-sm text-white">{model.name}</div>
                      <div className="text-[11px] text-slate-400 group-hover:text-blue-100">
                        {model.description}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-[#3B82F6] group-hover:text-white px-2 py-1 rounded bg-blue-500/10 group-hover:bg-white/20">
                    Gọi xe →
                  </span>
                </button>
              ))}
            </div>

            <p className="text-[11px] text-center text-slate-400 pt-1">
              ⚡ Chạm 1 lần để phát lệnh gọi xe AMR ngay lập tức
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
