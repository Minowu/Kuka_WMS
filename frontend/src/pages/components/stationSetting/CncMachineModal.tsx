import { PlusOutlined } from '@ant-design/icons';
import { Button, Form, Input, Modal } from '@/components/ui';
import type { NodeTools } from './stationSettingTypes';
import type { CncMachineFormState } from './useCncMachineForm';
import { MAX_CNC_SLOTS } from './cncSlotUtils';
import CncSlotRow from './CncSlotRow';

interface CncMachineModalProps {
  cnc: CncMachineFormState;
  nodeTools: NodeTools;
}

export default function CncMachineModal({ cnc, nodeTools }: CncMachineModalProps) {
  const isEdit = !!cnc.editingMachine;
  const selectedNodes = cnc.slots.map((s) => s.node_label);

  return (
    <Modal
      title={isEdit ? `Chỉnh sửa cấu hình ${cnc.editingMachine?.machine_code}` : 'Thêm Máy CNC Mới & Cấu hình Vị trí Đỗ'}
      open={cnc.isModalOpen}
      onCancel={cnc.closeModal}
      onOk={cnc.submit}
      confirmLoading={cnc.isSaving}
      okText={isEdit ? 'Lưu thay đổi' : 'Tạo máy & Lưu vị trí'}
      cancelText="Hủy"
      centered
      width={560}
    >
      <Form form={cnc.form} layout="vertical" className="mt-4">
        <div className="grid grid-cols-2 gap-3">
          {!isEdit && (
            <Form.Item
              name="machine_code"
              label="Mã máy CNC"
              rules={[{ required: true, message: 'Vui lòng nhập mã máy CNC!' }]}
            >
              <Input
                placeholder="Ví dụ: CNC-05"
                className="uppercase"
                onChange={(e) => cnc.changeMachineCode(e.target.value)}
              />
            </Form.Item>
          )}
          <Form.Item
            name="machine_name"
            label="Tên hiển thị máy"
            rules={[{ required: true, message: 'Vui lòng nhập tên máy!' }]}
          >
            <Input placeholder="Ví dụ: Máy Phay CNC 05" />
          </Form.Item>
        </div>

        <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 mb-3 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                Cấu hình Vị trí Đỗ (1 đến {MAX_CNC_SLOTS} Slots)
              </span>
              <p className="text-[11px] text-slate-500 m-0">
                {isEdit
                  ? 'Cập nhật Node Map hoặc mở rộng vị trí đỗ cho máy'
                  : 'Mỗi vị trí gắn với một Node Map KUKA để AMR điều phối phôi vào/ra'}
              </p>
            </div>

            {cnc.slots.length < MAX_CNC_SLOTS && (
              <Button
                variant="outline"
                icon={<PlusOutlined />}
                onClick={cnc.addSlot}
                className="!h-7 !text-xs !rounded-lg text-brand-primary border-brand-primary/40 hover:!bg-brand-primary/10"
              >
                Thêm vị trí đỗ
              </Button>
            )}
          </div>

          <div className="space-y-2.5">
            {cnc.slots.map((slot, idx) => (
              <CncSlotRow
                key={idx}
                slot={slot}
                canRemove={cnc.slots.length > 1}
                options={nodeTools.getNodeOptions({
                  currentLocationId: slot.id,
                  selectedInForm: selectedNodes,
                  currentSlotNode: slot.node_label,
                })}
                onNodeChange={(nodeLabel) => cnc.setSlotNode(idx, nodeLabel)}
                onOpenMap={() =>
                  nodeTools.openMapPicker({
                    title: `Chọn Node trên bản đồ cho POS${slot.position_index} (${cnc.getMachineCode()})`,
                    currentSelectedNodeLabel: slot.node_label,
                    currentLocationId: slot.id,
                    selectedInForm: selectedNodes,
                    onSelect: (node) => cnc.setSlotNode(idx, node.node_label),
                  })
                }
                onRemove={() => cnc.removeSlot(idx)}
              />
            ))}
          </div>
        </div>
      </Form>
    </Modal>
  );
}
