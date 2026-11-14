import type { MachineCatalogGroup } from '@/types/station';
import AreaSectionHeader from './AreaSectionHeader';
import CncMachineCheckCard from './CncMachineCheckCard';

interface CncMachineCheckListProps {
  machines: MachineCatalogGroup[];
  selectedSet: Set<number>;
  onToggleMachine: (slotIds: number[]) => void;
  onSelectAll: () => void;
  onClear: () => void;
}

export default function CncMachineCheckList({
  machines,
  selectedSet,
  onToggleMachine,
  onSelectAll,
  onClear,
}: CncMachineCheckListProps) {
  return (
    <div>
      <AreaSectionHeader
        title="Danh sách Máy CNC trong xưởng"
        description="Tích chọn máy nào sẽ tự động gán toàn bộ các vị trí đỗ (POS1, POS2, POS3) của máy đó"
        selectAllText="Chọn tất cả máy"
        selectAllClass="text-brand-primary hover:text-brand-primary"
        onSelectAll={onSelectAll}
        onClear={onClear}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {machines.map((machine) => (
          <CncMachineCheckCard
            key={machine.id}
            machine={machine}
            selectedSet={selectedSet}
            onToggle={onToggleMachine}
          />
        ))}
      </div>
    </div>
  );
}
