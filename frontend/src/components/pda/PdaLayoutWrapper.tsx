import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  WifiOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  FireOutlined,
} from '@ant-design/icons';
import { usePdaStore } from '@/store/usePdaStore';

interface PdaLayoutWrapperProps {
  title: string;
  badge?: string;
  children: React.ReactNode;
}

export const PdaLayoutWrapper: React.FC<PdaLayoutWrapperProps> = ({
  title,
  badge,
  children,
}) => {
  const location = useLocation();
  const [currentTime, setCurrentTime] = useState<string>('');
  const toast = usePdaStore((s) => s.toast);
  const hideToast = usePdaStore((s) => s.hideToast);

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

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => {
      hideToast();
    }, 3500);
    return () => clearTimeout(t);
  }, [toast, hideToast]);

  const navLinks = [
    { path: '/pda/raw-material', label: '📦 N.Liệu', key: 'raw_material' },
    { path: '/pda/cnc', label: '⚙️ Máy CNC', key: 'cnc_line' },
    { path: '/pda/washing', label: '🚿 Tẩy Rửa', key: 'washing_station' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-start items-center p-0 sm:py-6 select-none font-sans">
      <div className="w-full max-w-[480px] bg-slate-900 border-x sm:border border-slate-800 sm:rounded-3xl shadow-2xl flex flex-col min-h-screen sm:min-h-[860px] overflow-hidden relative">
        {/* Status header */}
        <header className="bg-slate-950 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#FF5800] ring-2 ring-[#FF5800]/30 animate-pulse" />
            <Link to="/caller" className="font-black tracking-wider text-white uppercase text-xs hover:text-[#FF5800]">
              KUKA AMR <span className="text-[#FF5800]">CALLER</span>
            </Link>
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

        {/* Thanh chọn nhanh Route dành cho PDA */}
        <div className="bg-slate-950/80 p-2 border-b border-slate-800/80">
          <div className="grid grid-cols-3 gap-1.5">
            {navLinks.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.key}
                  to={item.path}
                  className={`min-h-[46px] rounded-xl flex items-center justify-center font-bold text-xs transition-all active:scale-[0.97] ${
                    isActive
                      ? 'bg-[#FF5800] text-white shadow-lg shadow-[#FF5800]/30 ring-1 ring-[#FF5800]'
                      : 'bg-slate-800/70 hover:bg-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Thân giao diện */}
        <main className="flex-1 flex flex-col overflow-y-auto">{children}</main>

        {/* Footer PDA */}
        <footer className="bg-slate-950 px-4 py-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span>{title}</span>
          </div>
          {badge && (
            <span className="font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded text-[10px]">
              {badge}
            </span>
          )}
        </footer>

        {/* TOAST THÔNG BÁO 1 CHẠM */}
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
