import React, { useEffect } from 'react';
import { usePdaStore } from '@/store/usePdaStore';
import { useLogout } from '@/hooks/useAuth';

interface PdaLayoutWrapperProps {
  title: string;
  stationSubtitle?: string;
  children: React.ReactNode;
}

export const PdaLayoutWrapper: React.FC<PdaLayoutWrapperProps> = ({
  title,
  stationSubtitle,
  children,
}) => {
  const toast = usePdaStore((s) => s.toast);
  const hideToast = usePdaStore((s) => s.hideToast);
  const logout = useLogout();

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => {
      hideToast();
    }, 3500);
    return () => clearTimeout(t);
  }, [toast, hideToast]);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-start items-center p-0 sm:py-6 select-none font-sans">
      <div className="w-full max-w-[480px] bg-slate-900 border-x sm:border border-slate-800 sm:rounded-2xl shadow-2xl flex flex-col min-h-screen sm:min-h-[840px] overflow-hidden relative">
        {/* Header tinh giản công nghiệp: Không có đồng hồ, không có badge PDA, không có link chuyển phân xưởng */}
        <header className="bg-slate-950 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF5800]" />
            <div>
              <div className="font-bold text-white text-sm tracking-wide uppercase">
                {title}
              </div>
              {stationSubtitle && (
                <div className="text-[11px] text-slate-400 font-medium">
                  {stationSubtitle}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <span className="text-[11px] font-mono text-emerald-400 font-bold tracking-wider">
              ONLINE
            </span>
            <button
              onClick={logout}
              title="Đăng xuất ca làm việc"
              className="text-[11px] font-bold text-slate-400 hover:text-white px-2 py-0.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded active:scale-95 cursor-pointer"
            >
              Thoát
            </button>
          </div>
        </header>

        {/* Nội dung độc lập của màn hình phân xưởng */}
        <main className="flex-1 flex flex-col overflow-y-auto">
          {children}
        </main>

        {/* Toast thông báo dạng dải công nghiệp tinh gọn, không icon hoạt hình */}
        {toast && (
          <div className="fixed sm:absolute bottom-4 left-4 right-4 z-50">
            <div
              className={`p-3 rounded-xl shadow-xl flex items-center justify-between border ${
                toast.type === 'kuka'
                  ? 'bg-[#FF5800] text-white border-orange-400'
                  : toast.type === 'success'
                  ? 'bg-slate-900 border-emerald-500 text-emerald-300'
                  : toast.type === 'warning'
                  ? 'bg-slate-900 border-amber-500 text-amber-300'
                  : 'bg-slate-900 border-blue-500 text-blue-300'
              }`}
            >
              <div className="text-xs font-bold leading-snug">
                {toast.message}
              </div>
              <button
                onClick={hideToast}
                className="text-xs text-white/70 hover:text-white px-1.5 py-0.5 ml-2 cursor-pointer font-bold"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PdaLayoutWrapper;
