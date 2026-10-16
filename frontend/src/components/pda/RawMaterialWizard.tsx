import React, { useState } from 'react';
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
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    setRackId(`RCK-${selectedPosition}-${randomSuffix}`);
    setCurrentStep(3);
  };

  // Sinh ngẫu nhiên mã QR Rack để test
  const handleGenerateRandomQr = () => {
    if ('vibrate' in navigator) navigator.vibrate?.(30);
    const randomNum = Math.floor(1000 + Math.random() * 9000);
    const newId = `RCK-${selectedPosition || 'VT'}-${randomNum}`;
    setRackId(newId);
    showToast(`Đã nạp mã: ${newId}`, 'info');
  };

  // Quét QR qua Camera
  const handleCameraScanSuccess = (text: string) => {
    setIsScanningCamera(false);
    const cleanText = text.trim();
    setRackId(cleanText);
    showToast(`Đã nhận diện: ${cleanText}`, 'success');
  };

  // Bước 3: Xác nhận Cấp Phôi
  const handleConfirmSupply = () => {
    if (!rackId.trim()) {
      showToast('Vui lòng nhập hoặc quét mã Rack', 'warning');
      return;
    }

    if ('vibrate' in navigator) navigator.vibrate?.(60);

    onSupplyConfirm({
      positionId: selectedPosition,
      modelId: selectedModel,
      rackId: rackId.trim().toUpperCase(),
    });

    // Tự động quay về Bước 1
    setSelectedPosition('');
    setSelectedModel('');
    setRackId('');
    setCurrentStep(1);
  };

  return (
    <div className="flex flex-col flex-1 p-3">
      {/* Thanh tiến trình bước (Clean Steps) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-2 mb-3">
        <div className="grid grid-cols-3 gap-1 text-center font-bold text-xs">
          <div
            className={`py-1.5 rounded-lg ${
              currentStep === 1
                ? 'bg-[#FF5800] text-white'
                : 'text-slate-400 bg-slate-950'
            }`}
          >
            1. VỊ TRÍ
          </div>
          <div
            className={`py-1.5 rounded-lg ${
              currentStep === 2
                ? 'bg-[#FF5800] text-white'
                : 'text-slate-400 bg-slate-950'
            }`}
          >
            2. MODEL
          </div>
          <div
            className={`py-1.5 rounded-lg ${
              currentStep === 3
                ? 'bg-[#FF5800] text-white'
                : 'text-slate-400 bg-slate-950'
            }`}
          >
            3. QUÉT RACK
          </div>
        </div>
      </div>

      {/* ================= BƯỚC 1: CHỌN VỊ TRÍ (VT-01 đến VT-07) ================= */}
      {currentStep === 1 && (
        <div className="flex flex-col flex-1">
          <div className="mb-2 text-center">
            <h2 className="text-sm font-bold tracking-wider text-slate-300 uppercase">
              CHỌN VỊ TRÍ CẤP PHÔI
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-2 flex-1">
            {positions.map((pos) => {
              const isOccupied = pos.hasRack;
              return (
                <button
                  key={pos.id}
                  onClick={() => handleSelectPosition(pos.id)}
                  className={`min-h-[58px] p-3 rounded-xl border flex flex-col justify-center items-start text-left transition-all active:scale-[0.98] ${
                    isOccupied
                      ? 'bg-amber-950/20 border-amber-600/40 text-amber-200'
                      : 'bg-slate-800/90 border-slate-700 hover:border-[#FF5800] text-white'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xl font-bold font-mono text-white">
                      {pos.id}
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                        isOccupied
                          ? 'bg-amber-500/20 text-amber-300'
                          : 'bg-emerald-500/20 text-emerald-300'
                      }`}
                    >
                      {isOccupied ? 'CÓ RACK' : 'TRỐNG'}
                    </span>
                  </div>
                  {pos.currentModel ? (
                    <div className="text-[11px] text-slate-400 mt-1 truncate w-full font-mono">
                      {pos.currentModel} • {pos.currentRackId}
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-400 mt-0.5">Sẵn sàng nạp</div>
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
          <div className="flex items-center justify-between mb-2.5">
            <button
              onClick={() => setCurrentStep(1)}
              className="min-h-[44px] px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold border border-slate-700 active:scale-95"
            >
              ← Chọn lại Vị trí
            </button>
            <div className="text-xs font-mono font-bold text-slate-300 bg-slate-800 px-2 py-1 rounded">
              Vị trí: {selectedPosition}
            </div>
          </div>

          <div className="text-center mb-2">
            <h2 className="text-sm font-bold tracking-wider text-slate-300 uppercase">
              CHỌN MODEL PHÔI
            </h2>
          </div>

          <div className="flex flex-col gap-2 flex-1 overflow-y-auto pr-0.5">
            {models.map((model) => (
              <button
                key={model.id}
                onClick={() => handleSelectModel(model.id)}
                className="min-h-[54px] p-3 rounded-xl bg-slate-800 hover:bg-[#FF5800] border border-slate-700 hover:border-orange-500 text-left flex items-center justify-between group transition-all active:scale-[0.98]"
              >
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-lg bg-slate-900 group-hover:bg-black/30 text-white flex items-center justify-center font-bold text-xs font-mono">
                    {model.code}
                  </span>
                  <div>
                    <div className="font-bold text-sm text-white">{model.name}</div>
                    <div className="text-[11px] text-slate-400 group-hover:text-orange-100">
                      {model.description}
                    </div>
                  </div>
                </div>
                <span className="text-xs font-bold text-slate-400 group-hover:text-white">
                  Chọn →
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ================= BƯỚC 3: QUÉT QR RACK & XÁC NHẬN ================= */}
      {currentStep === 3 && (
        <div className="flex flex-col flex-1">
          <div className="flex items-center justify-between mb-2.5">
            <button
              onClick={() => setCurrentStep(2)}
              className="min-h-[44px] px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold border border-slate-700 active:scale-95"
            >
              ← Chọn lại Model
            </button>
            <div className="text-xs font-mono font-bold text-slate-300 bg-slate-800 px-2 py-1 rounded">
              {selectedPosition}
            </div>
          </div>

          <div className="bg-slate-800 rounded-xl p-3 border border-slate-700 mb-3 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Vị trí cấp:</span>
              <span className="font-bold font-mono text-white">{selectedPosition}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Model đã chọn:</span>
              <span className="font-bold text-[#FF5800]">
                {models.find((m) => m.id === selectedModel)?.name || selectedModel}
              </span>
            </div>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Mã Rack Phôi:
            </label>
            <input
              type="text"
              value={rackId}
              onChange={(e) => setRackId(e.target.value.toUpperCase())}
              placeholder="Nhập hoặc quét mã barcode/QR..."
              className="w-full min-h-[52px] bg-slate-950 border-2 border-[#FF5800]/70 focus:border-[#FF5800] rounded-xl px-3 text-base font-mono font-bold text-white placeholder-slate-600 outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-2 mb-4">
            <button
              onClick={() => setIsScanningCamera(true)}
              className="min-h-[48px] bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl font-bold text-xs active:scale-95"
            >
              Quét Camera
            </button>

            <button
              onClick={handleGenerateRandomQr}
              className="min-h-[48px] bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl font-bold text-xs active:scale-95"
            >
              Sinh Mã Test
            </button>
          </div>

          <div className="mt-auto pt-2">
            <button
              onClick={handleConfirmSupply}
              className="w-full min-h-[58px] bg-[#FF5800] hover:bg-[#e04e00] text-white rounded-xl font-bold text-base tracking-wide flex items-center justify-center shadow-lg active:scale-[0.98] transition-all cursor-pointer"
            >
              XÁC NHẬN CẤP PHÔI
            </button>
          </div>
        </div>
      )}

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
