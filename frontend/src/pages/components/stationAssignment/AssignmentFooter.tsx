import { CheckOutlined } from '@ant-design/icons';
import { Button, Space } from '@/components/ui';
import { AREA_NAMES, type ProductionArea } from './stationAssignmentConfig';

interface AssignmentFooterProps {
  selectedArea: ProductionArea;
  selectedCount: number;
  isSaving: boolean;
  onCancel: () => void;
  onSave: () => void;
}

export default function AssignmentFooter({
  selectedArea,
  selectedCount,
  isSaving,
  onCancel,
  onSave,
}: AssignmentFooterProps) {
  return (
    <div className="flex items-center justify-between w-full pt-2">
      <div className="text-xs text-slate-500 font-medium">
        Khu vực: <span className="font-bold text-slate-700">{AREA_NAMES[selectedArea]}</span> | Đã chọn:{' '}
        <span className="font-bold text-brand-primary text-sm">{selectedCount}</span> vị trí
      </div>
      <Space>
        <Button variant="outline" onClick={onCancel}>
          Hủy
        </Button>
        <Button variant="primary" onClick={onSave} loading={isSaving} icon={<CheckOutlined />}>
          Lưu Phân Quyền
        </Button>
      </Space>
    </div>
  );
}
