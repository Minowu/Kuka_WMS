import { useState } from 'react';
import { Form, message } from '@/components/ui';
import { useCreateMachine, useDeleteMachine, useUpdateMachine } from '@/hooks/useMachines';
import type { MachineCatalogGroup } from '@/types/station';
import { padTwoDigits } from '@/utils/number';
import type { NodeTools, SlotFormItem } from './stationSettingTypes';
import { showStationError } from './showStationError';
import {
  MAX_CNC_SLOTS,
  buildSlotCode,
  createDefaultSlots,
  normalizeMachineCode,
  reindexSlots,
  toSlotPayload,
} from './cncSlotUtils';

interface CncFormValues {
  machine_code?: string;
  machine_name: string;
}

/** Thêm / sửa / xóa máy CNC kèm danh sách 1..4 vị trí đỗ. Dùng chung một modal cho cả thêm và sửa. */
export function useCncMachineForm(machineCount: number, nodeTools: NodeTools) {
  const [form] = Form.useForm<CncFormValues>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMachine, setEditingMachine] = useState<MachineCatalogGroup | null>(null);
  const [slots, setSlots] = useState<SlotFormItem[]>([]);

  const createMutation = useCreateMachine();
  const updateMutation = useUpdateMachine();
  const deleteMutation = useDeleteMachine();

  const getMachineCode = () =>
    editingMachine?.machine_code ?? normalizeMachineCode(form.getFieldValue('machine_code'));

  const openCreate = () => {
    const nextNumber = padTwoDigits(machineCount + 1);
    const code = `CNC-${nextNumber}`;
    form.resetFields();
    form.setFieldsValue({ machine_code: code, machine_name: `Máy Phay CNC ${nextNumber}` });
    setEditingMachine(null);
    setSlots(createDefaultSlots(code));
    setIsModalOpen(true);
  };

  const openEdit = (machine: MachineCatalogGroup) => {
    form.resetFields();
    form.setFieldsValue({ machine_name: machine.machine_name || `Máy ${machine.machine_code}` });
    const currentSlots: SlotFormItem[] = (machine.slots || []).map((s, idx) => ({
      id: s.id,
      position_index: s.position_index || idx + 1,
      location_code: s.location_code,
      node_label: nodeTools.matchNodeLabel(s.node_label, s.location_code),
      map_x: s.map_x || undefined,
      map_y: s.map_y || undefined,
    }));
    setEditingMachine(machine);
    setSlots(currentSlots.length > 0 ? currentSlots : createDefaultSlots(machine.machine_code));
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const changeMachineCode = (value: string) => {
    const code = normalizeMachineCode(value);
    setSlots((prev) => prev.map((s) => ({ ...s, location_code: buildSlotCode(code, s.position_index) })));
  };

  const addSlot = () => {
    if (slots.length >= MAX_CNC_SLOTS) {
      message.warning(`Mỗi máy CNC hỗ trợ tối đa ${MAX_CNC_SLOTS} vị trí đỗ (POS1..POS${MAX_CNC_SLOTS})!`);
      return;
    }
    const position = slots.length + 1;
    setSlots((prev) => [...prev, { position_index: position, location_code: buildSlotCode(getMachineCode(), position) }]);
  };

  const removeSlot = (indexToRemove: number) => {
    if (slots.length <= 1) {
      message.warning('Máy CNC cần có ít nhất 1 vị trí đỗ!');
      return;
    }
    setSlots(reindexSlots(slots.filter((_, idx) => idx !== indexToRemove), getMachineCode()));
  };

  const setSlotNode = (slotIndex: number, nodeLabel: string) => {
    const node = nodeTools.availableNodes.find((n) => n.node_label === nodeLabel);
    setSlots((prev) =>
      prev.map((s, idx) =>
        idx === slotIndex ? { ...s, node_label: nodeLabel, map_x: node?.map_x, map_y: node?.map_y } : s
      )
    );
  };

  const submit = async () => {
    try {
      const values = await form.validateFields();
      const machineName = values.machine_name.trim();

      if (editingMachine) {
        await updateMutation.mutateAsync({
          id: editingMachine.id,
          data: { machine_name: machineName, slots: toSlotPayload(slots, editingMachine.machine_code) },
        });
        message.success(`Cập nhật cấu hình máy '${editingMachine.machine_code}' thành công!`);
      } else {
        const code = normalizeMachineCode(values.machine_code);
        await createMutation.mutateAsync({
          machine_code: code,
          machine_name: machineName,
          slots: toSlotPayload(slots, code),
        });
        message.success(`Thêm máy '${code}' cùng ${slots.length} vị trí đỗ thành công!`);
      }
      setIsModalOpen(false);
    } catch (err) {
      showStationError(err, editingMachine ? 'Không thể cập nhật máy CNC' : 'Không thể tạo máy CNC mới');
    }
  };

  const deleteMachine = async (machine: MachineCatalogGroup) => {
    try {
      await deleteMutation.mutateAsync(machine.id);
      message.success(`Đã xóa máy CNC '${machine.machine_code}'`);
    } catch (err) {
      showStationError(err, 'Không thể xóa máy CNC');
    }
  };

  return {
    form,
    isModalOpen,
    editingMachine,
    slots,
    isSaving: createMutation.isPending || updateMutation.isPending,
    getMachineCode,
    openCreate,
    openEdit,
    closeModal,
    changeMachineCode,
    addSlot,
    removeSlot,
    setSlotNode,
    submit,
    deleteMachine,
  };
}

export type CncMachineFormState = ReturnType<typeof useCncMachineForm>;
