import type { ReactNode } from 'react';
import { Segmented, Tag } from 'antd';
import { ExperimentOutlined, InboxOutlined, ToolOutlined } from '@ant-design/icons';
import type { StationCatalogResponse } from '@/types/station';
import type { ProductionArea } from './stationAssignmentConfig';

interface AreaOption {
  value: ProductionArea;
  icon: ReactNode;
  text: string;
  tagColor: string;
  getCountText: (catalog: StationCatalogResponse) => string;
}

const AREA_OPTIONS: AreaOption[] = [
  {
    value: 'raw_material',
    icon: <InboxOutlined className="text-amber-600 text-base" />,
    text: '📦 Khu Cấp Phôi',
    tagColor: 'orange',
    getCountText: (c) => `${c.raw_materials?.length || 0}`,
  },
  {
    value: 'cnc',
    icon: <ToolOutlined className="text-brand-primary text-base" />,
    text: '⚙️ Khu Máy CNC',
    tagColor: 'blue',
    getCountText: (c) => `${c.machines?.length || 0} máy`,
  },
  {
    value: 'washing',
    icon: <ExperimentOutlined className="text-emerald-600 text-base" />,
    text: '🧼 Khu Tẩy Rửa',
    tagColor: 'green',
    getCountText: (c) => `${c.washing_slots?.length || 0}`,
  },
];

interface AreaSelectorProps {
  catalog: StationCatalogResponse;
  value: ProductionArea;
  /** Khu bị khóa theo role; null = được chọn tự do */
  roleArea: ProductionArea | null;
  onChange: (area: ProductionArea) => void;
}

export default function AreaSelector({ catalog, value, roleArea, onChange }: AreaSelectorProps) {
  const isLockedByRole = roleArea !== null;

  return (
    <Segmented
      block
      size="large"
      value={value}
      onChange={(val) => onChange(val as ProductionArea)}
      disabled={isLockedByRole}
      className="p-1 bg-slate-100 rounded-xl font-bold [&_.ant-segmented-item-selected]:!bg-white [&_.ant-segmented-item-selected]:!text-brand-primary [&_.ant-segmented-item-selected]:!shadow-sm"
      options={AREA_OPTIONS.map((option) => ({
        value: option.value,
        disabled: isLockedByRole && roleArea !== option.value,
        label: (
          <div className="flex items-center justify-center gap-2 py-1.5">
            {option.icon}
            <span className="text-sm">{option.text}</span>
            <Tag color={option.tagColor} className="!ml-1 !mr-0 !px-1.5 !text-[11px] !font-bold">
              {option.getCountText(catalog)}
            </Tag>
          </div>
        ),
      }))}
    />
  );
}
