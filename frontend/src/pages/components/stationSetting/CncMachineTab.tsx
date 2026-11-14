import type { MachineCatalogGroup } from '@/types/station';
import type { BannerTheme, NodeTools } from './stationSettingTypes';
import { useCncMachineForm } from './useCncMachineForm';
import ZoneInfoBanner from './ZoneInfoBanner';
import CncMachineCard from './CncMachineCard';
import CncMachineModal from './CncMachineModal';

const CNC_BANNER_THEME: BannerTheme = {
  bannerClass: 'bg-blue-50/70 border-blue-200',
  iconClass: 'text-blue-600',
  textClass: 'text-blue-900',
  buttonClass: '!bg-brand-primary hover:!bg-stripe-primary-deep',
};

interface CncMachineTabProps {
  machines: MachineCatalogGroup[];
  nodeTools: NodeTools;
}

export default function CncMachineTab({ machines, nodeTools }: CncMachineTabProps) {
  const cnc = useCncMachineForm(machines.length, nodeTools);

  return (
    <div className="space-y-4">
      <ZoneInfoBanner
        theme={CNC_BANNER_THEME}
        title="Mô hình CNC linh hoạt 1..4 Slots:"
        buttonText="Thêm Máy CNC"
        onAdd={cnc.openCreate}
      >
        Mỗi máy CNC có thể cấu hình linh hoạt từ 1 đến 4 vị trí đỗ vật lý (
        <span className="font-semibold text-blue-700">POS1, POS2, POS3, POS4</span>), gắn tương ứng với Node Map
        KUKA. Công đoạn gia công không gắn cứng vào máy mà được quản lý linh hoạt trong trang{' '}
        <span className="font-semibold underline">Quy trình (Route)</span>.
      </ZoneInfoBanner>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {machines.map((machine) => (
          <CncMachineCard key={machine.id} machine={machine} onEdit={cnc.openEdit} onDelete={cnc.deleteMachine} />
        ))}
      </div>

      <CncMachineModal cnc={cnc} nodeTools={nodeTools} />
    </div>
  );
}
