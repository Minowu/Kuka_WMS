import { Checkbox } from 'antd';
import { cn } from '@/components/ui';
import type { StationCatalogItem } from '@/types/station';
import type { LocationGridTheme } from './stationAssignmentConfig';
import AreaSectionHeader from './AreaSectionHeader';

interface LocationCheckGridProps {
  theme: LocationGridTheme;
  items: StationCatalogItem[];
  selectedSet: Set<number>;
  onToggle: (id: number) => void;
  onSelectAll: () => void;
  onClear: () => void;
}

/** Lưới chọn từng vị trí đơn (Khu Cấp Phôi, Khu Tẩy Rửa). */
export default function LocationCheckGrid({
  theme,
  items,
  selectedSet,
  onToggle,
  onSelectAll,
  onClear,
}: LocationCheckGridProps) {
  return (
    <div>
      <AreaSectionHeader
        title={theme.title}
        note={`(Đã chọn ${selectedSet.size}/${items.length})`}
        selectAllText="Chọn tất cả"
        selectAllClass={theme.selectAllClass}
        onSelectAll={onSelectAll}
        onClear={onClear}
      />

      <div className={`grid gap-2.5 ${theme.gridClass}`}>
        {items.map((slot) => {
          const isSelected = selectedSet.has(slot.id);
          return (
            <div
              key={slot.id}
              onClick={() => onToggle(slot.id)}
              className={cn(
                'flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer text-xs transition-all select-none',
                isSelected
                  ? theme.selectedItemClass
                  : 'border-slate-200 bg-white hover:border-slate-300 text-slate-600'
              )}
            >
              <Checkbox checked={isSelected} className="pointer-events-none" />
              <div className="min-w-0 flex-1">
                <div className="font-mono font-bold text-slate-800">{slot.location_name}</div>
                <div className="text-[10px] text-slate-400 truncate">{slot.location_code}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
