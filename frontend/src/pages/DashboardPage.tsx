import React, { useState } from 'react';
import WarehouseMapCanvas from '@/components/shared/WarehouseMapCanvas';
import { useReportKpis } from '@/hooks/useDashboard';
import { useAppStore } from '@/store/useAppStore';
import {
  InboxOutlined,
  SyncOutlined,
  FieldTimeOutlined,
  CheckCircleOutlined,
  DownOutlined,
  UpOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

export default function DashboardPage() {
  const selectedWarehouseId = useAppStore((s) => s.selectedWarehouseId);
  const { data: kpiData, isLoading } = useReportKpis(selectedWarehouseId);
  const [showKpiBar, setShowKpiBar] = useState(true);

  const activeCarts = kpiData?.active_carts_count ?? 0;
  const inTransitAmr = kpiData?.in_transit_amr_count ?? 0;
  const queuedRequests = kpiData?.queued_requests_count ?? 0;
  const completedToday = kpiData?.parts_completed_today ?? 0;

  return (
    <div className="flex flex-col h-full w-full bg-slate-900 overflow-hidden">
      {/* ── Top Bar: Workshop Realtime KPI Summary ── */}
      <div className="bg-slate-800/90 border-b border-slate-700/80 px-4 py-2 transition-all duration-300">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Giám sát xưởng CNC & AMR realtime
            </span>
          </div>
          <button
            onClick={() => setShowKpiBar(!showKpiBar)}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors px-2 py-0.5 rounded bg-slate-700/50 hover:bg-slate-700"
          >
            {showKpiBar ? (
              <>
                <span>Thu gọn</span>
                <UpOutlined className="text-[10px]" />
              </>
            ) : (
              <>
                <span>Xem chỉ số ({activeCarts} xe WIP)</span>
                <DownOutlined className="text-[10px]" />
              </>
            )}
          </button>
        </div>

        {showKpiBar && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1 pb-1">
            {/* Card 1: Xe phôi trên chuyền */}
            <div className="bg-slate-900/80 border border-slate-700/70 rounded-lg p-2.5 flex items-center justify-between shadow-sm">
              <div>
                <p className="text-[11px] text-slate-400 font-medium mb-0.5">Xe phôi WIP trên chuyền</p>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-bold text-sky-400">
                    {isLoading ? '...' : activeCarts}
                  </span>
                  <span className="text-[11px] text-slate-500">xe gá</span>
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 text-base">
                <InboxOutlined />
              </div>
            </div>

            {/* Card 2: Lệnh AMR đang chạy */}
            <div className="bg-slate-900/80 border border-slate-700/70 rounded-lg p-2.5 flex items-center justify-between shadow-sm">
              <div>
                <p className="text-[11px] text-slate-400 font-medium mb-0.5">Lệnh AMR đang chạy</p>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-bold text-amber-400">
                    {isLoading ? '...' : inTransitAmr}
                  </span>
                  <span className="text-[11px] text-slate-500">nhiệm vụ</span>
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-base">
                <SyncOutlined spin={inTransitAmr > 0} />
              </div>
            </div>

            {/* Card 3: Hàng đợi gọi xe */}
            <div className="bg-slate-900/80 border border-slate-700/70 rounded-lg p-2.5 flex items-center justify-between shadow-sm">
              <div>
                <p className="text-[11px] text-slate-400 font-medium mb-0.5">Hàng đợi chờ điều phối</p>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-bold text-orange-400">
                    {isLoading ? '...' : queuedRequests}
                  </span>
                  <span className="text-[11px] text-slate-500">yêu cầu</span>
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 text-base">
                <FieldTimeOutlined />
              </div>
            </div>

            {/* Card 4: Sản lượng hoàn thành hôm nay */}
            <div className="bg-slate-900/80 border border-slate-700/70 rounded-lg p-2.5 flex items-center justify-between shadow-sm">
              <div>
                <p className="text-[11px] text-slate-400 font-medium mb-0.5">Công đoạn xong hôm nay</p>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-xl font-bold text-emerald-400">
                    {isLoading ? '...' : completedToday}
                  </span>
                  <span className="text-[11px] text-slate-500">lần hoàn tất</span>
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-base">
                <CheckCircleOutlined />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── 2D Interactive Warehouse Map Canvas ── */}
      <div className="flex-1 w-full min-h-0 relative">
        <WarehouseMapCanvas />
      </div>
    </div>
  );
}
