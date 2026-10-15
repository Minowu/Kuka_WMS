import React, { useState } from 'react';
import {
  QrcodeOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  CameraOutlined,
} from '@ant-design/icons';
import { QrCameraOverlay } from '@/components/qr-scan/QrCameraOverlay';
import type { PartModel, RawMaterialPosition } from '@/types/pda';

interface RawMaterialWizardProps {
  positions: RawMaterialPosition[];
  models: PartModel[];
  onSupplyConfirm: (data: { positionId: string; modelId: string; rackId: string }) => void;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
}

export const RawMaterialWizard: React.FC<RawMaterialWizardProps> = ({
  positions,
  models,
  onSupplyConfirm,
  showToast,
}) => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [selectedPosition, setSelectedPosition] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [rackId, setRackId] = useState<string>('');
  const [isScanningCamera, setIsScanningCamera] = useState<boolean>(false);

  // Bước 1: 1-Chạm Chọn Vị Trí -> Chuyển ngay Bước 2
  const handleSelectPosition = (posId: string) => {
    if ('vibrate' in navigator) navigator.vibrate?.(30);
    setSelectedPosition(posId);
    setCurrentStep(2);
  };

  // Bước 2: 1-Chạm Chọn Model -> Chuyển ngay Bước 3
  const handleSelectModel = (modelId: string) => {
    if ('vibrate' in navigator) navigator.vibrate?.(30);
    setSelectedModel(modelId);
    // Tự sinh mã Rack gợi ý tiện cho thao tác nhanh nếu chưa có
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    setRackId(`RCK-${selectedPosition}-${randomSuffix}`);
    setCurrentStep(3);
  };

  // Sinh ngẫu nhiên mã QR Rack để test tức thì
  const handleGenerateRandomQr = () => {
    if ('vibrate' in navigator) navigator.vibrate?.(30);
    const randomNum = Math.floor(1000 + Math.random() * 9000);
    const newId = `RCK-${selectedPosition || 'VT'}-${randomNum}`;
    setRackId(newId);
    showToast(`Đã nạp mã mẫu: ${newId}`, 'info');
  };

  // Hoàn tất quét QR qua Camera
  const handleCameraScanSuccess = (text: string) => {
    setIsScanningCamera(false);
    const cleanText = text.trim();
    setRackId(cleanText);
    showToast(`Đã nhận diện QR: ${cleanText}`, 'success');
  };

  // Bước 3: Xác nhận Cấp Phôi -> 1 Chạm không hỏi lại
  const handleConfirmSupply = () => {
    if (!rackId.trim()) {
      showToast('Vui lòng quét hoặc nhập mã QR Rack', 'warning');
      return;
    }

    if ('vibrate' in navigator) navigator.vibrate?.(60);

    onSupplyConfirm({
      positionId: selectedPosition,
      modelId: selectedModel,
      rackId: rackId.trim().toUpperCase(),
    });

    showToast(
      `Đã cấp phôi thành công: [${selectedPosition}] - ${selectedModel} - ${rackId.toUpperCase()}`,
      'success'
    );

    // Tự động quay về Bước 1 để sẵn sàng cho lần quét tiếp theo
    setSelectedPosition('');
    setSelectedModel('');
    setRackId('');
    setCurrentStep(1);
  };

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Wizard Progress Bar */}
      <div className="bg-slate-800/80 rounded-xl p-2.5 mb-3 border border-slate-700/60 shadow-sm">
        <div className="flex items-center justify-between text-xs font-semibold">
          <div
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${
              currentStep === 1
                ? 'bg-[#FF5800] text-white font-bold'
                : 'text-slate-400 bg-slate-900/50'
            }`}
          >
            <span className="w-4 h-4 rounded-full bg-black/30 flex items-center justify-center text-[10px]">
              1
            </span>
            <span>Vị Trí</span>
          </div>

          <div className="w-4 h-[2px] bg-slate-700" />

          <div
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${
              currentStep === 2
                ? 'bg-[#FF5800] text-white font-bold'
                : 'text-slate-400 bg-slate-900/50'
            }`}
          >
            <span className="w-4 h-4 rounded-full bg-black/30 flex items-center justify-center text-[10px]">
              2
            </span>
            <span>Model</span>
          </div>

          <div className="w-4 h-[2px] bg-slate-700" />

          <div
            className={`flex items-center gap-1.5 px-2 py-1 rounded-lg ${
              currentStep === 3
                ? 'bg-[#FF5800] text-white font-bold'
                : 'text-slate-400 bg-slate-900/50'
            }`}
          >
            <span className="w-4 h-4 rounded-full bg-black/30 flex items-center justify-center text-[10px]">
              3
            </span>
            <span>Quét QR</span>
          </div>
        </div>
      </div>

      {/* ================= BƯỚC 1: CHỌN VỊ TRÍ (VT-01 đến VT-07) ================= */}
      {currentStep === 1 && (
        <div className="flex flex-col flex-1">
          <div className="mb-2 text-center">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">
              Bước 1 / 3
            </span>
            <h2 className="text-lg font-bold text-white flex items-center justify-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#FF5800]" />
              CHỌN VỊ TRÍ CẤP PHÔI
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Chạm 1 lần để chọn vị trí khay/bàn</p>
          </div>

          {/* 7 Nút to bản [VT-01] đến [VT-07] */}
          <div className="grid grid-cols-2 gap-2.5 flex-1">
            {positions.map((pos) => {
              const isOccupied = pos.hasRack;
              return (
                <button
                  key={pos.id}
                  onClick={() => handleSelectPosition(pos.id)}
                  className={`min-h-[58px] p-3 rounded-xl border flex flex-col justify-center items-start text-left transition-all active:scale-[0.98] ${
                    isOccupied
                      ? 'bg-amber-950/30 border-amber-500/40 hover:border-amber-500 text-amber-200'
                      : 'bg-slate-800/90 border-slate-700 hover:border-[#FF5800] text-white'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xl font-black tracking-wide text-white font-mono">
                      {pos.id}
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                        isOccupied
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {isOccupied ? 'Đang có Rack' : 'Sẵn sàng'}
                    </span>
                  </div>
                  {pos.currentModel && (
                    <div className="text-[11px] text-slate-400 mt-1 truncate w-full">
                      {pos.currentModel} • {pos.currentRackId}
                    </div>
                  )}
                  {!pos.currentModel && (
                    <div className="text-[11px] text-slate-400 mt-0.5">Vị trí phôi trống</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ================= BƯỚC 2: CHỌN MODEL (Model 1 đến Model 7) ================= */}
      {currentStep === 2 && (
        <div className="flex flex-col flex-1">
          {/* Header & Back Button */}
          <div className="flex items-center justify-between mb-2">
            <button
              onClick={() => setCurrentStep(1)}
              className="min-h-[46px] px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl flex items-center gap-1.5 text-xs font-bold border border-slate-700 active:scale-95 transition-all"
            >
              <ArrowLeftOutlined /> Quay lại VT
            </button>
            <div className="text-right">
              <span className="text-xs text-slate-400">Đang chọn cho</span>
              <span className="ml-1.5 text-sm font-black text-[#FF5800] bg-[#FF5800]/10 px-2 py-0.5 rounded-lg border border-[#FF5800]/30 font-mono">
                {selectedPosition}
              </span>
            </div>
          </div>

          <div className="mb-2 text-center">
            <span className="text-xs uppercase tracking-wider text-slate-400 font-medium">
              Bước 2 / 3
            </span>
            <h2 className="text-lg font-bold text-white flex items-center justify-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#FF5800]" />
              CHỌN MODEL PHÔI
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">Chạm 1 lần để chọn mã linh kiện</p>
          </div>

          {/* Danh sách 7 Model */}
          <div className="flex flex-col gap-2 flex-1 overflow-y-auto pr-0.5">
            {models.map((model) => (
              <button
                key={model.id}
                onClick={() => handleSelectModel(model.id)}
                className="min-h-[52px] p-3 rounded-xl bg-slate-800/90 border border-slate-700 hover:border-[#FF5800] text-left flex items-center justify-between transition-all active:scale-[0.98] group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-slate-700/80 group-hover:bg-[#FF5800] text-slate-200 group-hover:text-white flex items-center justify-center font-bold text-sm font-mono transition-colors">
                    {model.code}
                  </div>
                  <div>
                    <div className="font-bold text-sm text-white">{model.name}</div>
                    <div className="text-[11px] text-slate-400">{model.description}</div>
                  </div>
                </div>
                <div className="text-xs font-bold text-[#FF5800] opacity-80 group-hover:opacity-100 flex items-center gap-1">
                  Chọn →
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ================= BƯỚC 3: QUÉT QR RACK & XÁC NHẬN ================= */}
      {currentStep === 3 && (
        <div className="flex flex-col flex-1">
          {/* Header & Back Button */}
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setCurrentStep(2)}
              className="min-h-[46px] px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl flex items-center gap-1.5 text-xs font-bold border border-slate-700 active:scale-95 transition-all"
            >
              <ArrowLeftOutlined /> Đổi Model
            </button>
            <div className="text-xs text-slate-400 font-medium">Bước 3 / 3</div>
          </div>

          {/* Tóm tắt thông tin đã chọn */}
          <div className="bg-slate-800/90 rounded-xl p-3 border border-slate-700 mb-3 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Vị trí cấp phôi:</span>
              <span className="font-black text-white bg-slate-700 px-2 py-0.5 rounded font-mono text-sm">
                {selectedPosition}
              </span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Model đã chọn:</span>
              <span className="font-bold text-[#FF5800] bg-[#FF5800]/10 px-2 py-0.5 rounded border border-[#FF5800]/30 text-xs">
                {models.find((m) => m.id === selectedModel)?.name || selectedModel}
              </span>
            </div>
          </div>

          {/* Ô Hiển thị / Nhập mã Rack ID */}
          <div className="mb-3">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
              Mã QR Rack Phôi:
            </label>
            <div className="relative">
              <input
                type="text"
                value={rackId}
                onChange={(e) => setRackId(e.target.value.toUpperCase())}
                placeholder="Nhập hoặc quét mã QR..."
                className="w-full min-h-[52px] bg-slate-950 border-2 border-[#FF5800]/60 focus:border-[#FF5800] rounded-xl px-3.5 text-base font-mono font-bold text-white placeholder-slate-500 outline-none"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {rackId && (
                  <button
                    onClick={() => setRackId('')}
                    className="text-xs px-2 py-1 text-slate-400 hover:text-white"
                  >
                    Xóa
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Các nút hỗ trợ quét nhanh */}
          <div className="grid grid-cols-2 gap-2 mb-4">
            <button
              onClick={() => setIsScanningCamera(true)}
              className="min-h-[52px] bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 rounded-xl font-bold text-xs flex items-center justify-center gap-2 active:scale-95 transition-all"
            >
              <CameraOutlined className="text-base" />
              <span>Quét Camera</span>
            </button>

            <button
              onClick={handleGenerateRandomQr}
              className="min-h-[52px] bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded-xl font-bold text-xs flex items-center justify-center gap-2 active:scale-95 transition-all"
            >
              <ThunderboltOutlined className="text-base" />
              <span>Sinh Mã Mẫu</span>
            </button>
          </div>

          {/* Nút Cực To XÁC NHẬN CẤP PHÔI */}
          <div className="mt-auto pt-2">
            <button
              onClick={handleConfirmSupply}
              className="w-full min-h-[58px] bg-[#FF5800] hover:bg-[#e04e00] text-white rounded-xl font-black text-base tracking-wide flex items-center justify-center gap-2.5 shadow-lg shadow-[#FF5800]/25 active:scale-[0.98] transition-all"
            >
              <CheckCircleOutlined className="text-xl" />
              <span>XÁC NHẬN CẤP PHÔI</span>
            </button>
            <p className="text-[11px] text-center text-slate-400 mt-2">
              ⚡ 1 Chạm kích hoạt ngay - Tự động quay lại Bước 1 sau khi nạp
            </p>
          </div>
        </div>
      )}

      {/* Overlay Camera Quét QR nếu người dùng mở camera */}
      {isScanningCamera && (
        <QrCameraOverlay
          title="Quét QR Rack Phôi"
          onScan={handleCameraScanSuccess}
          onClose={() => setIsScanningCamera(false)}
        />
      )}
    </div>
  );
};
