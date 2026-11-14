import { MinusCircleOutlined } from '@ant-design/icons';
import { Button } from '@/components/ui';
import type { NodeOption, SlotFormItem } from './stationSettingTypes';
import NodeSelectWithMap from './NodeSelectWithMap';
import PosBadge from '@/components/shared/PosBadge';

interface CncSlotRowProps {
  slot: SlotFormItem;
  options: NodeOption[];
  canRemove: boolean;
  onNodeChange: (nodeLabel: string) => void;
  onOpenMap: () => void;
  onRemove: () => void;
}

export default function CncSlotRow({ slot, options, canRemove, onNodeChange, onOpenMap, onRemove }: CncSlotRowProps) {
  return (
    <div className="bg-white border border-slate-200/80 rounded-lg p-2.5 flex items-center justify-between gap-3 shadow-2xs">
      <div className="flex items-center gap-2">
        <PosBadge position={slot.position_index} />
        <span className="font-mono text-xs font-bold text-slate-700">
          {slot.location_code || `POS${slot.position_index}`}
        </span>
      </div>

      <div className="flex-1 max-w-[320px]">
        <NodeSelectWithMap
          compact
          value={slot.node_label}
          onChange={onNodeChange}
          options={options}
          placeholder={`Chọn Node cho POS${slot.position_index}`}
          onOpenMap={onOpenMap}
        />
      </div>

      {canRemove && (
        <Button
          variant="ghost"
          icon={<MinusCircleOutlined className="text-slate-400 hover:text-red-500" />}
          onClick={onRemove}
          className="!h-7 !w-7 !p-0"
          title="Xóa vị trí này"
        />
      )}
    </div>
  );
}
