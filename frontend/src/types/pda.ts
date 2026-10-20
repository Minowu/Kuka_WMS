export type PdaArea = 'raw_material' | 'cnc_line' | 'washing_station';

export interface RawMaterialPosition {
  id: string; // 'RAW-01' -> 'RAW-07' hoặc 'VT-01'
  locationId?: number;
  name: string;
  hasRack: boolean;
  currentRackId?: string;
  currentModel?: string;
}

export interface PartModel {
  id: string | number; // 'MDL-01' hoặc ID 42
  itemId?: number;
  code: string;
  name: string;
  description: string;
  standardQuantityPerCart?: number;
}

export interface CncMachineStation {
  id: string; // 'CNC-01-POS1' -> 'CNC-04-POS2'
  locationId?: number;
  machineCode?: string; // 'CNC-01' -> 'CNC-04'
  positionIndex?: number; // 1 hoặc 2
  name: string;
  assignedStageLevel: number; // Cấp độ công đoạn ĐƯỢC CHỈ ĐỊNH cho máy này
  stageName: string; // Tên công đoạn: 'Phay Thô', 'Phay Tinh', 'Khoan Tappi & Hoàn Tất'
  status: 'EMPTY' | 'CALLING' | 'OCCUPIED';
  callingModel?: string;
  callingTaskCode?: string;
  currentRack?: {
    rackId: string;
    model: string;
    level: number; // Cấp độ hiện tại của phôi trên xe
    startedAt?: string;
  } | null;
}

export interface WashingSlot {
  id: number; // 1 -> 4
  locationId?: number;
  code?: string; // 'WASH-01' -> 'WASH-04'
  name: string; // 'Slot 1' -> 'Slot 4'
  status: 'EMPTY' | 'OCCUPIED';
  currentRack?: {
    rackId: string;
    model: string;
    fromStation: string;
    arrivedAt: string;
  } | null;
}

export interface PdaToastNotification {
  id: string;
  message: string;
  type: 'success' | 'info' | 'warning' | 'kuka';
  timestamp: number;
}
