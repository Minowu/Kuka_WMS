/**
 * TYPES CHO QUẢN TRỊ MÁY CNC & VỊ TRÍ ĐỖ CỦA MÁY (MACHINES & SLOTS)
 */

export interface SlotConfigInput {
  id?: number;
  position_index: number;
  location_code?: string;
  location_name?: string;
  node_label?: string;
  map_x?: number;
  map_y?: number;
}

export interface MachineSlotInfo {
  id: number;
  location_code: string;
  location_label?: string | null;
  location_name: string | null;
  position_index: number | null;
  node_label?: string | null;
  map_x: number | null;
  map_y: number | null;
  is_active?: boolean;
}

export interface MachineItem {
  id: number;
  machine_code: string;
  machine_name: string | null;
  warehouse_id: number | null;
  is_active?: boolean;
  location_count: number;
  positions: string[];
  slots: MachineSlotInfo[];
}

export interface MachineCreateInput {
  machine_code: string;
  machine_name?: string;
  warehouse_id?: number;
  slots?: SlotConfigInput[];
}

export interface MachineUpdateInput {
  machine_name?: string;
  is_active?: boolean;
  slots?: SlotConfigInput[];
}
