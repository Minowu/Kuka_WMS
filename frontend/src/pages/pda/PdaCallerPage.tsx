import React, { useState, useEffect } from 'react';
import {
  WifiOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  FireOutlined,
} from '@ant-design/icons';
import { RawMaterialWizard } from '@/components/pda/RawMaterialWizard';
import { CncLineModal } from '@/components/pda/CncLineModal';
import { WashingStationModal } from '@/components/pda/WashingStationModal';
import type { PdaArea } from '@/types/pda';
import { usePdaStore } from '@/store/usePdaStore';

export const PdaCallerPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<PdaArea>('raw_material');
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleTimeString('vi-VN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        })
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const positions = usePdaStore((s) => s.positions);
  const models = usePdaStore((s) => s.models);
  const cncStations = usePdaStore((s) => s.cncStations);
  const washingSlots = usePdaStore((s) => s.washingSlots);
  const toast = usePdaStore((s) => s.toast);
  const showToast = usePdaStore((s) => s.showToast);
  const hideToast = usePdaStore((s) => s.hideToast);

  const supplyRawMaterial = usePdaStore((s) => s.supplyRawMaterial);
  const callMaterialToCnc = usePdaStore((s) => s.callMaterialToCnc);
  const fastArriveCnc = usePdaStore((s) => s.fastArriveCnc);
  const updateCncStageLevel = usePdaStore((s) => s.updateCncStageLevel);
  const releaseWashingSlot = usePdaStore((s) => s.releaseWashingSlot);
  const simulateArriveWashing = usePdaStore((s) => s.simulateArriveWashing);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => {
      hideToast();
    }, 3500);
    return () => clearTimeout(t);
  }, [toast, hideToast]);

  const activeCncCount = cncStations.filter((s) => s.status !== 'EMPTY').length;
  const washingOccupiedCount = washingSlots.filter((s) => s.status === 'OCCUPIED').length;
  const rawMaterialOccupiedCount = positions.filter((p) => p.hasRack).length;

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-start items-center p-0 sm:py-6 select-none font-sans">
      <div className="w-full max-w-[480px] bg-slate-900 border-x sm:border border-slate-800 sm:rounded-3xl shadow-2xl flex flex-col min-h-screen sm:min-h-[860px] overflow-hidden relative">
        {/* Status Header */}
        <header className="bg-slate-950 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#FF5800] ring-2 ring-[#FF5800]/30 animate-pulse" />
            <span className="font-black tracking-wider text-white uppercase text-xs">
              KUKA AMR <span className="text-[#FF5800]">CALLER</span>
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded font-mono">
              PDA-4.2"
            </span>
          </div>

          <div className="flex items-center gap-3 text-slate-400">
            <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-bold font-mono">
              <WifiOutlined /> ONLINE
            </span>
            <span className="text-[11px] font-mono font-bold text-slate-200">
              {currentTime || '08:00:00'}
            </span>
          </div>
        </header>

        {/* Tab switcher */}
        <div className="bg-slate-950/80 p-2 border-b border-slate-800/80">
          <div className="grid grid-cols-3 gap-1.5">
            <button
              onClick={() => {
                if ('vibrate' in navigator) navigator.vibrate?.(20);
                setActiveTab('raw_material');
              }}
              className={`min-h-[52px] rounded-xl flex flex-col items-center justify-center font-black transition-all active:scale-[0.97] relative ${
                activeTab === 'raw_material'
                  ? 'bg-[#FF5800] text-white shadow-lg shadow-[#FF5800]/30 ring-1 ring-[#FF5800]'
                  : 'bg-slate-800/70 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="text-sm tracking-wide">📦 N.LIỆU</span>
              <span className="text-[10px] font-mono opacity-90">
                {rawMaterialOccupiedCount}/7 Rack
              </span>
            </button>

            <button
              onClick={() => {
                if ('vibrate' in navigator) navigator.vibrate?.(20);
                setActiveTab('cnc_line');
              }}
              className={`min-h-[52px] rounded-xl flex flex-col items-center justify-center font-black transition-all active:scale-[0.97] relative ${
                activeTab === 'cnc_line'
                  ? 'bg-[#3B82F6] text-white shadow-lg shadow-blue-500/30 ring-1 ring-blue-500'
                  : 'bg-slate-800/70 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="text-sm tracking-wide">⚙️ MÁY CNC</span>
              <span className="text-[10px] font-mono opacity-90">
                {activeCncCount}/4 Trạm
              </span>
            </button>

            <button
              onClick={() => {
                if ('vibrate' in navigator) navigator.vibrate?.(20);
                setActiveTab('washing_station');
              }}
              className={`min-h-[52px] rounded-xl flex flex-col items-center justify-center font-black transition-all active:scale-[0.97] relative ${
                activeTab === 'washing_station'
                  ? 'bg-[#10B981] text-white shadow-lg shadow-emerald-500/30 ring-1 ring-emerald-500'
                  : 'bg-slate-800/70 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="text-sm tracking-wide">🚿 TẨY RỬA</span>
              <span className="text-[10px] font-mono opacity-90">
                {washingOccupiedCount}/4 Slot
              </span>
            </button>
          </div>
        </div>

        {/* Thân giao diện */}
        <main className="flex-1 flex flex-col overflow-y-auto">
          {activeTab === 'raw_material' && (
            <RawMaterialWizard
              positions={positions}
              models={models}
              onSupplyConfirm={supplyRawMaterial}
              showToast={showToast}
            />
          )}

          {activeTab === 'cnc_line' && (
            <CncLineModal
              stations={cncStations}
              models={models}
              onCallMaterial={callMaterialToCnc}
              onUpdateLevel={updateCncStageLevel}
              onFastArrive={fastArriveCnc}
              showToast={showToast}
            />
          )}

          {activeTab === 'washing_station' && (
            <WashingStationModal
              slots={washingSlots}
              onReleaseSlot={releaseWashingSlot}
              onSimulateArrive={simulateArriveWashing}
              showToast={showToast}
            />
          )}
        </main>

        {/* Footer PDA */}
        <footer className="bg-slate-950 px-4 py-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>KUKA Fleet Adapter: Ready</span>
          </div>
          <span className="font-mono text-slate-400">AMR-KUKA-01</span>
        </footer>

        {/* Floating Toast */}
        {toast && (
          <div className="fixed sm:absolute bottom-4 left-4 right-4 z-50 animate-in fade-in slide-in-from-bottom duration-200">
            <div
              className={`p-3.5 rounded-2xl shadow-2xl flex items-center gap-3 border ${
                toast.type === 'kuka'
                  ? 'bg-gradient-to-r from-[#FF5800] to-[#E04D00] text-white border-orange-400 shadow-orange-500/30'
                  : toast.type === 'success'
                  ? 'bg-slate-900 border-emerald-500 text-emerald-300 shadow-emerald-500/20'
                  : toast.type === 'warning'
                  ? 'bg-slate-900 border-amber-500 text-amber-300 shadow-amber-500/20'
                  : 'bg-slate-900 border-blue-500 text-blue-300 shadow-blue-500/20'
              }`}
            >
              <div className="text-xl flex-shrink-0">
                {toast.type === 'kuka' && <FireOutlined className="animate-bounce" />}
                {toast.type === 'success' && <CheckCircleOutlined />}
                {toast.type === 'warning' && <WarningOutlined />}
                {toast.type === 'info' && <InfoCircleOutlined />}
              </div>
              <div className="text-xs font-bold flex-1 leading-snug">
                {toast.message}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PdaCallerPage;
