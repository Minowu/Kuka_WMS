import type { SlotConfigInput } from '@/types/machine';
import type { SlotFormItem } from './stationSettingTypes';

export const MAX_CNC_SLOTS = 4;

export const normalizeMachineCode = (value?: string) => (value || 'CNC-XX').toUpperCase().trim();

export const buildSlotCode = (machineCode: string, position: number) => `${machineCode}-POS${position}`;

export function createDefaultSlots(machineCode: string): SlotFormItem[] {
  return [1, 2].map((position) => ({
    position_index: position,
    location_code: buildSlotCode(machineCode, position),
  }));
}

/** Đánh lại số POS1..POSn liên tục sau khi xóa một slot. */
export function reindexSlots(slots: SlotFormItem[], machineCode: string): SlotFormItem[] {
  return slots.map((slot, idx) => ({
    ...slot,
    position_index: idx + 1,
    location_code: buildSlotCode(machineCode, idx + 1),
  }));
}

export function toSlotPayload(slots: SlotFormItem[], machineCode: string): SlotConfigInput[] {
  return slots.map((slot) => ({
    id: slot.id,
    position_index: slot.position_index,
    location_code: slot.location_code || buildSlotCode(machineCode, slot.position_index),
    node_label: slot.node_label,
    map_x: slot.map_x,
    map_y: slot.map_y,
  }));
}
