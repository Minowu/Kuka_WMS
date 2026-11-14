import { CheckSquareOutlined, ClearOutlined } from '@ant-design/icons';
import { Button, Space } from '@/components/ui';

interface AreaSectionHeaderProps {
  title: string;
  /** Ghi chú nhỏ cạnh tiêu đề, ví dụ "(Đã chọn 2/7)" */
  note?: string;
  /** Mô tả một dòng bên dưới tiêu đề */
  description?: string;
  selectAllText: string;
  selectAllClass: string;
  onSelectAll: () => void;
  onClear: () => void;
}

export default function AreaSectionHeader({
  title,
  note,
  description,
  selectAllText,
  selectAllClass,
  onSelectAll,
  onClear,
}: AreaSectionHeaderProps) {
  return (
    <div className="flex items-center justify-between border-b border-slate-200 pb-2.5 mb-3">
      <div>
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-800 text-sm">{title}</span>
          {note && <span className="text-xs text-slate-400">{note}</span>}
        </div>
        {description && <p className="text-[11px] text-slate-500 m-0">{description}</p>}
      </div>

      <Space size="small">
        <Button
          variant="outline"
          icon={<CheckSquareOutlined />}
          onClick={onSelectAll}
          className={`!h-7 !text-xs !rounded-lg ${selectAllClass}`}
        >
          {selectAllText}
        </Button>
        <Button
          variant="outline"
          icon={<ClearOutlined />}
          onClick={onClear}
          className="!h-7 !text-xs !rounded-lg hover:text-red-500"
        >
          Bỏ chọn tất cả
        </Button>
      </Space>
    </div>
  );
}
