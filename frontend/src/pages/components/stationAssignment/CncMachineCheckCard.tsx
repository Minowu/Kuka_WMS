import { Checkbox, Tag } from 'antd';
import { cn } from '@/components/ui';
import PosBadge from '@/components/shared/PosBadge';
import type { MachineCatalogGroup } from '@/types/station';

interface CncMachineCheckCardProps {
  machine: MachineCatalogGroup;
  selectedSet: Set<number>;
  onToggle: (slotIds: number[]) => void;
}

export default function CncMachineCheckCard({ machine, selectedSet, onToggle }: CncMachineCheckCardProps) {
  const slots = machine.slots || [];
  const slotIds = slots.map((s) => s.id);
  const allSelected = slotIds.length > 0 && slotIds.every((id) => selectedSet.has(id));
  const partiallySelected = !allSelected && slotIds.some((id) => selectedSet.has(id));

  return (
    <div
      onClick={() => onToggle(slotIds)}
      className={cn(
        'border rounded-xl transition-all p-3 cursor-pointer select-none',
        allSelected
          ? 'border-brand-primary/60 bg-orange-50/20 shadow-xs'
          : partiallySelected
            ? 'border-blue-300 bg-blue-50/10'
            : 'border-slate-200 bg-white hover:border-slate-300'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2.5">
          <Checkbox checked={allSelected} indeterminate={partiallySelected} className="pointer-events-none" />
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-slate-800 text-sm">{machine.machine_code}</span>
            <span className="text-xs text-slate-400">
              ({machine.machine_name || `Máy ${machine.machine_code}`})
            </span>
          </div>
        </div>
        <Tag color="blue" className="!text-[11px] !font-bold !m-0">
          {slots.length} Vị trí
        </Tag>
      </div>

      <div className="flex flex-wrap gap-1.5 pl-6">
        {slots.map((slot, sIdx) => (
          <div
            key={slot.id || sIdx}
            className={cn(
              'flex items-center gap-1 px-2 py-1 rounded-md text-[11px] border font-mono transition-colors',
              selectedSet.has(slot.id)
                ? 'bg-orange-100/60 border-orange-200 text-orange-950 font-semibold'
                : 'bg-slate-50 border-slate-100 text-slate-500'
            )}
          >
            <PosBadge position={slot.position_index || sIdx + 1} size="small" />
            <span>{slot.location_code}</span>
            {slot.node_label && <span className="text-[10px] text-slate-400">(Node {slot.node_label})</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
