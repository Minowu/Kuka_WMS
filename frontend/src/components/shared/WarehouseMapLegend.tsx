import React from 'react';
import {
  NODE_NORMAL_COLOR,
  SHELF_EMPTY_COLOR,
  SHELF_FULL_COLOR,
  SHELF_STROKE_COLOR,
} from '@/utils/warehouseMapUtils';

const LEGEND_ITEMS = [
  {
    key: 'waypoint',
    label: 'Waypoint',
    shape: 'circle' as const,
    color: NODE_NORMAL_COLOR,
    border: undefined,
    borderStyle: 'solid',
  },
  {
    key: 'empty',
    label: 'Vị trí trống',
    shape: 'square' as const,
    color: SHELF_EMPTY_COLOR,
    border: SHELF_STROKE_COLOR,
    borderStyle: 'solid',
  },
  {
    key: 'has_stock',
    label: 'Có xe phôi',
    shape: 'square' as const,
    color: SHELF_FULL_COLOR,
    border: '#059669',
    borderStyle: 'solid',
  },
  {
    key: 'reserved',
    label: 'Giữ chỗ',
    shape: 'square' as const,
    color: '#fef3c7',
    border: '#d97706',
    borderStyle: 'dashed',
  },
  {
    key: 'in_transit',
    label: 'Đang luân chuyển',
    shape: 'square' as const,
    color: '#dbeafe',
    border: '#2563eb',
    borderStyle: 'dashed',
  },
];

const WarehouseMapLegend: React.FC = () => {
  return (
    <div className="absolute bottom-3 right-3 z-20 flex max-w-[min(100%-1.5rem,36rem)] flex-wrap items-center justify-end gap-x-3 gap-y-1.5 rounded-lg border border-slate-200 bg-white/90 px-3 py-2 shadow-md backdrop-blur-sm pointer-events-none select-none">
      {LEGEND_ITEMS.map((item) => (
        <div key={item.key} className="flex items-center gap-1.5">
          {item.shape === 'circle' ? (
            <div
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
          ) : (
            <div
              className="h-3 w-3 rounded-xs border"
              style={{
                backgroundColor: item.color,
                borderColor: item.border,
                borderStyle: item.borderStyle,
              }}
            />
          )}
          <span className="text-xs font-medium text-slate-700 whitespace-nowrap">
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
};

export default WarehouseMapLegend;
