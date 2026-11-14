import { Badge, Popconfirm } from 'antd';
import { DeleteOutlined, EditOutlined, ToolOutlined } from '@ant-design/icons';
import { Button, Card, Space } from '@/components/ui';
import type { MachineCatalogGroup } from '@/types/station';
import PosBadge from '@/components/shared/PosBadge';

const SLOT_BOX_CLASSES: Record<number, string> = {
  1: 'border-blue-200 bg-blue-50/30',
  2: 'border-purple-200 bg-purple-50/30',
  3: 'border-amber-200 bg-amber-50/30',
};
const DEFAULT_SLOT_BOX_CLASS = 'border-emerald-200 bg-emerald-50/30';

const SLOT_DOT_COLORS: Record<number, string> = { 1: '#3B82F6', 2: '#8B5CF6' };
const DEFAULT_SLOT_DOT_COLOR = '#F59E0B';

interface CncMachineCardProps {
  machine: MachineCatalogGroup;
  onEdit: (machine: MachineCatalogGroup) => void;
  onDelete: (machine: MachineCatalogGroup) => void;
}

export default function CncMachineCard({ machine, onEdit, onDelete }: CncMachineCardProps) {
  const slots = machine.slots || [];

  return (
    <Card className="shadow-sm border-slate-200/80 rounded-xl hover:shadow-md transition-shadow overflow-hidden bg-white">
      <div className="flex items-start justify-between border-b border-slate-100 pb-3 mb-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-orange-50 border border-orange-200 flex items-center justify-center text-brand-primary text-xl font-bold">
            <ToolOutlined />
          </div>
          <div>
            <span className="text-lg font-bold text-slate-800">{machine.machine_code}</span>
            <div className="text-xs text-slate-500 font-medium mt-0.5">
              {machine.machine_name || `Máy ${machine.machine_code}`}
            </div>
          </div>
        </div>

        <Space size="small">
          <Button
            variant="outline"
            icon={<EditOutlined />}
            onClick={() => onEdit(machine)}
            className="!h-8 !px-2.5 !rounded-lg text-slate-600 hover:text-brand-primary"
          >
            Sửa
          </Button>
          <Popconfirm
            title={`Xóa máy CNC ${machine.machine_code}?`}
            description="Xóa máy sẽ đồng thời xóa các vị trí đỗ liên kết."
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
            onConfirm={() => onDelete(machine)}
          >
            <Button
              variant="outline"
              icon={<DeleteOutlined className="text-red-500" />}
              className="!h-8 !px-2 hover:border-red-400"
            />
          </Popconfirm>
        </Space>
      </div>

      <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        <span>Vị trí đỗ vật lý ({slots.length} Slots)</span>
        <span className="text-slate-400 font-normal">Gắn Node Map KUKA</span>
      </div>

      <div className={`grid gap-2.5 ${slots.length === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
        {slots.map((slot, sIdx) => {
          const pos = slot.position_index || sIdx + 1;
          return (
            <div
              key={slot.id || sIdx}
              className={`border rounded-lg p-2.5 ${SLOT_BOX_CLASSES[pos] || DEFAULT_SLOT_BOX_CLASS}`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <PosBadge position={pos} />
                  <span className="font-mono text-xs font-bold text-slate-800 truncate">{slot.location_code}</span>
                </div>
                <Badge status="processing" color={SLOT_DOT_COLORS[pos] || DEFAULT_SLOT_DOT_COLOR} />
              </div>

              <div className="text-[11px] text-slate-600 mt-1.5 space-y-0.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Node:</span>
                  <span className="font-mono font-semibold text-slate-700">
                    {slot.node_label ? `Node ${slot.node_label}` : 'Chưa gán'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Tọa độ:</span>
                  <span className="font-mono text-[10px] text-slate-500">
                    {slot.map_x != null ? `${slot.map_x}, ${slot.map_y}` : '--'}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
