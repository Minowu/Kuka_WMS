import { EnvironmentOutlined } from '@ant-design/icons';
import { Button, Select, Space } from '@/components/ui';
import type { NodeOption } from './stationSettingTypes';

interface NodeSelectWithMapProps {
  value?: string;
  onChange?: (value: string) => void;
  options: NodeOption[];
  placeholder: string;
  onOpenMap: () => void;
  compact?: boolean;
}

/** Dùng được trong Form.Item (nhận value/onChange tự động) hoặc điều khiển trực tiếp qua props. */
export default function NodeSelectWithMap({
  value,
  onChange,
  options,
  placeholder,
  onOpenMap,
  compact = false,
}: NodeSelectWithMapProps) {
  return (
    <Space.Compact style={{ width: '100%' }}>
      <Select
        showSearch
        size={compact ? 'small' : undefined}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        options={options}
        filterOption={(input, option) =>
          String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
        }
        className={compact ? 'text-xs' : undefined}
        style={{ width: compact ? 'calc(100% - 75px)' : 'calc(100% - 90px)' }}
      />
      <Button
        size={compact ? 'small' : undefined}
        icon={<EnvironmentOutlined className="text-brand-primary" />}
        onClick={onOpenMap}
        className={
          compact
            ? '!text-xs font-medium text-brand-primary'
            : '!text-xs font-semibold text-brand-primary border-brand-primary/40 hover:!border-brand-primary'
        }
      >
        Bản đồ
      </Button>
    </Space.Compact>
  );
}
