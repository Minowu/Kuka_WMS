import React, { useState } from 'react';
import type { CncMachineStation, CncSupportedModel, PartModel } from '@/types/pda';

interface CncLineModalProps {
  stations: CncMachineStation[];
  models?: PartModel[];
  onCallMaterial: (stationId: string, itemId: number) => void;
  onUpdateLevel: (stationId: string) => void;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
}

export const CncLineModal: React.FC<CncLineModalProps> = ({
  stations,
  models: _models,
  onCallMaterial,
  onUpdateLevel,
  showToast,
}) => {
  // Modal chọn Model khi trạm hỗ trợ >= 2 Model
  const [selectedStationForModal, setSelectedStationForModal] = useState<CncMachineStation | null>(null);
  const [updatingStationId, setUpdatingStationId] = useState<string | null>(null);

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

  // Thao tác bấm nút "Gọi phôi"
  const handleCallButtonClick = (station: CncMachineStation) => {
    if ('vibrate' in navigator) navigator.vibrate?.(40);

    const supported = station.supportedModels || [];
    if (supported.length === 0) {
      showToast(`Máy [${station.name}] chưa được gán vào Quy trình sản xuất nào!`, 'warning');
      return;
    }

    if (supported.length === 1) {
      // 1-Chạm: Tự động gọi ngay Model duy nhất
      onCallMaterial(station.id, supported[0].itemId);
      return;
    }

    // Nhiều hơn 1 Model: Mở dialog chọn Model
    setSelectedStationForModal(station);
  };

  // Chọn Model trong Dialog
  const handleSelectModelFromModal = (stationId: string, model: CncSupportedModel) => {
    if ('vibrate' in navigator) navigator.vibrate?.(50);
    setSelectedStationForModal(null);
    onCallMaterial(stationId, model.itemId);
  };

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Danh sách trạm CNC */}
      <div className="flex flex-col gap-3 flex-1 overflow-y-auto pr-0.5">
        {stations.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center my-auto bg-slate-900/60 border border-slate-800 rounded-2xl">
            <div className="w-14 h-14 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-2xl mb-3 shadow-inner">
              🔒
            </div>
            <div className="text-white font-bold text-base mb-1.5">
              Chưa Được Phân Công Máy CNC
            </div>
            <div className="text-slate-400 text-xs leading-relaxed max-w-xs">
              Tài khoản của bạn chưa được gán máy CNC nào. Vui lòng liên hệ Quản đốc xưởng để được phân quyền máy phụ trách.
            </div>
          </div>
        ) : (
          stations.map((st) => {
            const isEmpty = st.status === 'EMPTY';
            const isQueued = st.status === 'QUEUED';
            const isCalling = st.status === 'CALLING';
            const isOccupied = st.status === 'OCCUPIED';
            const rack = st.currentRack;
            const isFinalStep = Boolean(st.isFinalStep);
            const supported = st.supportedModels || [];

            return (
              <div
                key={st.id}
                className={`rounded-xl border p-3 transition-all ${
                  isEmpty
                    ? 'bg-slate-900/90 border-slate-800'
                    : isCalling
                    ? 'bg-blue-950/20 border-blue-500/50'
                    : isQueued
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
                  {isQueued && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      ĐANG CHỜ AMR
                    </span>
                  )}
                  {isCalling && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      AMR ĐANG CHỞ TỚI
                    </span>
                  )}
                  {isOccupied && rack?.isCompleted ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                      ĐÃ BÁO XONG - CHỜ AMR
                    </span>
                  ) : isOccupied && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      ĐANG GIA CÔNG
                    </span>
                  )}
                </div>

                {/* 1. TRẠNG THÁI: TRỐNG -> GỌI PHÔI */}
                {isEmpty && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>
                        Sản phẩm hỗ trợ:{' '}
                        <span className="text-white font-bold">
                          {supported.length === 1
                            ? supported[0].modelCode
                            : supported.length > 1
                            ? `${supported.length} Model khả dụng`
                            : 'Chưa cấu hình'}
                        </span>
                      </span>
                      {supported.length === 1 && (
                        <span className="text-slate-300 font-mono text-[10px]">
                          Yêu cầu: {supported[0].inputStageLevel === 0 ? 'Phôi thô L0' : `Phôi L${supported[0].inputStageLevel}`}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => handleCallButtonClick(st)}
                      className="w-full min-h-[50px] bg-[#3B82F6] hover:bg-blue-600 text-white rounded-xl font-bold text-sm tracking-wide active:scale-[0.98] transition-all cursor-pointer shadow-md flex items-center justify-center gap-2"
                    >
                      <span>GỌI PHÔI (ĐIỀU AMR ĐẾN)</span>
                      {supported.length > 1 && (
                        <span className="text-xs bg-blue-900/80 px-2 py-0.5 rounded-full border border-blue-400/40">
                          {supported.length} Model ▼
                        </span>
                      )}
                    </button>
                  </div>
                )}

                {/* 2. TRẠNG THÁI: ĐANG CHỜ LƯỢT (QUEUED) HOẶC AMR ĐANG CHỞ TỚI (CALLING) */}
                {isQueued && (
                  <div className="space-y-2.5">
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
                      <div className="text-slate-400">Model đang yêu cầu:</div>
                      <div className="font-bold text-[#FF5800] mt-0.5 text-sm">
                        {st.callingModel || 'Phôi tiêu chuẩn'}
                      </div>
                      {st.callingTaskCode && (
                        <div className="text-[10px] text-slate-500 font-mono mt-1">
                          Lệnh: {st.callingTaskCode}
                        </div>
                      )}
                    </div>
                    <div className="w-full min-h-[46px] bg-amber-500/10 border border-amber-500/30 text-amber-300 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 px-3 py-2">
                      <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                      <span>Đã tiếp nhận yêu cầu, đang xếp hàng chờ AMR...</span>
                    </div>
                  </div>
                )}

                {isCalling && (
                  <div className="space-y-2.5">
                    <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
                      <div className="text-slate-400">Model đang vận chuyển:</div>
                      <div className="font-bold text-blue-400 mt-0.5 text-sm">
                        {st.callingModel || 'Phôi tiêu chuẩn'}
                      </div>
                      {st.callingTaskCode && (
                        <div className="text-[10px] text-blue-400/60 font-mono mt-1">
                          AMR Mission: {st.callingTaskCode}
                        </div>
                      )}
                    </div>
                    <div className="w-full min-h-[46px] bg-blue-500/10 border border-blue-500/30 text-blue-300 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 px-3 py-2">
                      <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                      <span>AMR đã nhận nhiệm vụ và đang chở phôi tới máy!</span>
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

                    {rack.isCompleted ? (
                      <div className="w-full min-h-[52px] bg-purple-950/40 border border-purple-500/40 text-purple-200 font-semibold text-xs rounded-xl flex flex-col items-center justify-center p-2.5 space-y-1 shadow-inner">
                        <div className="flex items-center gap-2 font-bold text-sm text-purple-300">
                          <span className="inline-block w-2.5 h-2.5 rounded-full bg-purple-400 animate-ping" />
                          <span>ĐÃ BÁO HOÀN THÀNH LEVEL {rack.level}</span>
                        </div>
                        <div className="text-[11px] text-purple-300/80">
                          {isFinalStep
                            ? 'Lệnh điều xe đã tạo: Đang chờ AMR đến lấy khay chuyển sang Khu Tẩy Rửa'
                            : 'Đang chờ AMR vận chuyển khay sang công đoạn tiếp theo'}
                          {rack.lockedByMission && (
                            <span className="block font-mono text-[10px] text-purple-400 mt-0.5">
                              Mission: {rack.lockedByMission}
                            </span>
                          )}
                        </div>
                      </div>
                    ) : (
                      <button
                        disabled={updatingStationId === st.id}
                        onClick={async () => {
                          if (updatingStationId === st.id) return;
                          if ('vibrate' in navigator) navigator.vibrate?.(60);
                          setUpdatingStationId(st.id);
                          try {
                            await onUpdateLevel(st.id);
                          } finally {
                            setUpdatingStationId(null);
                          }
                        }}
                        className={`w-full min-h-[54px] text-white rounded-xl font-bold text-sm tracking-wide transition-all ${
                          updatingStationId === st.id
                            ? 'bg-slate-700 cursor-not-allowed opacity-80'
                            : isFinalStep
                            ? 'bg-[#FF5800] hover:bg-[#e04e00] active:scale-[0.98] cursor-pointer'
                            : 'bg-[#10B981] hover:bg-[#059669] active:scale-[0.98] cursor-pointer'
                        }`}
                      >
                        {updatingStationId === st.id ? (
                          <div className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            <span>ĐANG CẬP NHẬT...</span>
                          </div>
                        ) : isFinalStep ? (
                          `BÁO XONG: CẬP NHẬT LEVEL ${st.assignedStageLevel} (CHUYỂN TẨY RỬA)`
                        ) : (
                          `BÁO XONG: CẬP NHẬT LEVEL ${st.assignedStageLevel}`
                        )}
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* MODAL / BOTTOM SHEET CHỌN MODEL KHI MÁY CÓ NHIỀU HƠN 1 MODEL */}
      {selectedStationForModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-end sm:items-center justify-center p-0 sm:p-4 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 w-full max-w-md rounded-t-2xl sm:rounded-2xl p-4 shadow-2xl flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div>
                <h3 className="text-base font-bold text-white">CHỌN MODEL SẢN PHẨM</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Gọi phôi gia công tới <span className="text-blue-400 font-mono font-bold">[{selectedStationForModal.name}]</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedStationForModal(null)}
                className="w-8 h-8 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-col gap-2.5 overflow-y-auto py-1">
              {(selectedStationForModal.supportedModels || []).map((m) => (
                <button
                  key={`${m.itemId}-${m.stageLevel}`}
                  onClick={() => handleSelectModelFromModal(selectedStationForModal.id, m)}
                  className="w-full p-3.5 rounded-xl bg-slate-950 hover:bg-slate-800/90 border border-slate-800 hover:border-[#3B82F6] text-left transition-all active:scale-[0.98] group flex items-center justify-between"
                >
                  <div className="flex-1 pr-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono font-bold text-white text-sm bg-blue-950/80 text-blue-300 border border-blue-700/50 px-2 py-0.5 rounded">
                        {m.modelCode}
                      </span>
                      <span className="text-xs font-bold text-slate-300 truncate">
                        {m.modelName}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-3">
                      <span>Công đoạn: <strong className="text-slate-200">Level {m.stageLevel}</strong></span>
                      <span>•</span>
                      <span>Đầu vào: <strong className="text-amber-400">{m.inputStageLevel === 0 ? 'Phôi thô L0' : `Phôi L${m.inputStageLevel}`}</strong></span>
                    </div>
                  </div>

                  <span className="text-xs font-bold text-blue-400 group-hover:text-blue-300 flex items-center gap-1 shrink-0 bg-blue-500/10 px-2.5 py-1.5 rounded-lg border border-blue-500/20">
                    Gọi xe →
                  </span>
                </button>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-800 mt-2">
              <button
                onClick={() => setSelectedStationForModal(null)}
                className="w-full min-h-[44px] bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-xl"
              >
                HỦY BỎ
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
