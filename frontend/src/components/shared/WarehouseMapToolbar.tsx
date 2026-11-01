import React from 'react';
import { Button } from '@/components/ui';

// ─── Props ─────────────────────────────────────────────────────────────────────

interface WarehouseMapToolbarProps {
  isAdmin: boolean;
  hasData: boolean;
  isLoading: boolean;
  errorMessage: string | null;
  nodesCount: number;
  linesCount: number | undefined;
  downloadLoading: boolean;
  onImportClick: () => void;
  onDownloadClick: () => void;
}

// ─── Component ─────────────────────────────────────────────────────────────────

const WarehouseMapToolbar: React.FC<WarehouseMapToolbarProps> = ({
  isAdmin,
  hasData,
  isLoading,
  errorMessage,
  nodesCount,
  linesCount,
  downloadLoading,
  onImportClick,
  onDownloadClick,
}) => {
  return (
    <div className="flex items-center gap-4 px-5 py-3 border-b border-slate-200 bg-white/60 backdrop-blur-sm shrink-0 rounded-t-xl">
      {/* Logo / Title */}
      <div className="flex items-center gap-2 mr-2">
        <div className="w-7 h-7 rounded bg-[#4a6fa5] flex items-center justify-center text-white text-xs font-bold shadow">
          M
        </div>
        <span className="text-slate-700 font-semibold text-sm tracking-wide">Warehouse Map</span>
      </div>

      {/* Import button — admin only */}
      {isAdmin && (
        <Button
          variant="primary"
          onClick={onImportClick}
          className="h-8! text-xs!"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Import Map
        </Button>
      )}

      {/* Download button — visible to all when map exists */}
      {hasData && (
        <Button
          variant="secondary"
          onClick={onDownloadClick}
          loading={downloadLoading}
          className="h-8! text-xs!"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Tải bản đồ
        </Button>
      )}

      {/* Status badges */}
      {isLoading && (
        <span className="text-xs text-amber-600 animate-pulse">⏳ Đang tải...</span>
      )}
      {hasData && !isLoading && (
        <span className="text-xs text-emerald-600">
          ✓ {nodesCount.toLocaleString()} nodes · {linesCount !== undefined ? `${linesCount.toLocaleString()} lines` : ''}
        </span>
      )}
      {errorMessage && (
        <span className="text-xs text-red-500 max-w-sm truncate">⚠ {errorMessage}</span>
      )}

      <div className="ml-auto hidden sm:flex items-center gap-1 text-slate-400 text-xs">
        <kbd className="px-1 py-0.5 rounded bg-slate-100 font-mono text-[10px] text-slate-500">scroll</kbd>
        <span>zoom</span>
        <span className="mx-1">·</span>
        <kbd className="px-1 py-0.5 rounded bg-slate-100 font-mono text-[10px] text-slate-500">drag</kbd>
        <span>pan</span>
      </div>
    </div>
  );
};

export default WarehouseMapToolbar;