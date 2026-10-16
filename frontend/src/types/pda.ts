export type PdaArea = 'raw_material' | 'cnc_line' | 'washing_station';

export interface RawMaterialPosition {
  id: string; // 'VT-01' -> 'VT-07'
  name: string;
  hasRack: boolean;
  currentRackId?: string;
  currentModel?: string;
}

export interface PartModel {
  id: string; // 'Model 1' -> 'Model 7'
  code: string;
  name: string;
  description: string;
}

export interface CncMachineStation {
  id: string; // 'CNC01_POS1' -> 'CNC04_POS2'
  machineCode?: string; // 'CNC-01' -> 'CNC-04'
  positionIndex?: number; // 1 hoặc 2
  name: string;
  assignedStageLevel: number; // Cấp độ công đoạn ĐƯỢC CHỈ ĐỊNH cho máy này (VD: CNC-01: 1, CNC-02: 1, CNC-03: 2, CNC-04: 3)
  stageName: string; // Tên công đoạn: 'Phay thô', 'Phay tinh', 'Hoàn tất CNC'
  status: 'EMPTY' | 'CALLING' | 'OCCUPIED';
  callingModel?: string;
  currentRack?: {
    rackId: string;
    model: string;
    level: number; // Cấp độ hiện tại của phôi trên xe (0: Phôi thô, 1: Xong B1, 2: Xong B2, 3: Hoàn tất)
    startedAt?: string;
  } | null;
}

export interface WashingSlot {
  id: number; // 1 -> 4
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
