export interface AvailableMapNode {
  node_number: number;
  node_label: string;
  map_x: number;
  map_y: number;
  function_type?: number | string | null;
  is_assigned?: boolean;
  assigned_to?: string | null;
}

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

export interface StationCatalogItem {
  id: number;
  location_code: string;
  location_label?: string | null;
  location_name: string | null;
  location_type: string;
  machine_code?: string | null;
  position_index?: number | null;
  node_label?: string | null;
  map_x: number | null;
  map_y: number | null;
  is_active?: boolean;
}

export interface MachineCatalogGroup {
  id: number;
  machine_code: string;
  machine_name: string | null;
  is_active?: boolean;
  slots: StationCatalogItem[];
}

export interface StationCatalogResponse {
  machines: MachineCatalogGroup[];
  raw_materials: StationCatalogItem[];
  washing_slots: StationCatalogItem[];
  empty_buffers?: StationCatalogItem[];
  buffer_slots?: StationCatalogItem[];
}

export interface StationLocationCreateInput {
  location_code: string;
  location_name?: string;
  location_type: 'RAW_MATERIAL' | 'WASHING_SLOT' | 'EMPTY_CART_BUFFER' | 'CNC_SLOT';
  node_label?: string;
  map_x?: number;
  map_y?: number;
  position_index?: number;
  machine_code?: string;
  warehouse_id?: number;
}

export interface StationLocationUpdateInput {
  location_name?: string;
  node_label?: string;
  map_x?: number;
  map_y?: number;
  position_index?: number;
  is_active?: boolean;
}
