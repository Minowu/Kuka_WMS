import React from 'react';
import {
  NODE_NORMAL_COLOR,
  SHELF_EMPTY_COLOR,
  SHELF_FULL_COLOR,
  SHELF_STROKE_COLOR,
  SHELF_SELECTED_COLOR,
  SHELF_SELECTED_STROKE_COLOR,
} from '@/utils/warehouseMapUtils';

const DEFAULT_LEGEND_ITEMS = [
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

const PICKER_LEGEND_ITEMS = [
  {
    key: 'selectable',
    label: 'Có thể chọn (Khả dụng)',
    shape: 'square' as const,
    color: '#ecfdf5',
    border: '#10b981',
    borderStyle: 'solid',
  },
  {
    key: 'selected',
    label: 'Đang chọn',
    shape: 'square' as const,
    color: SHELF_SELECTED_COLOR,
    border: SHELF_SELECTED_STROKE_COLOR,
    borderStyle: 'solid',
  },
  {
    key: 'assigned',
    label: 'Đã gán trạm khác',
    shape: 'square' as const,
    color: '#f1f5f9',
    border: '#cbd5e1',
    borderStyle: 'solid',
  },
  {
    key: 'waypoint',
    label: 'Điểm dẫn đường',
    shape: 'circle' as const,
    color: NODE_NORMAL_COLOR,
    border: undefined,
    borderStyle: 'solid',
  },
];

interface WarehouseMapLegendProps {
  isPickerMode?: boolean;
}

const WarehouseMapLegend: React.FC<WarehouseMapLegendProps> = ({ isPickerMode = false }) => {
  const items = isPickerMode ? PICKER_LEGEND_ITEMS : DEFAULT_LEGEND_ITEMS;

  return (
    <div className="absolute bottom-3 right-3 z-20 flex max-w-[min(100%-1.5rem,36rem)] flex-wrap items-center justify-end gap-x-3 gap-y-1.5 rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-md backdrop-blur-sm pointer-events-none select-none">
      {items.map((item) => (
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
