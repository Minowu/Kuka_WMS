export interface AndonRawMaterialDemand {
  id: number;
  requestCode: string;
  modelCode: string;
  modelName: string;
  machineCode: string;
  machineName: string;
  positionIndex?: number | null;
  destinationLocationCode: string;
  calledAt: string; // HH:mm:ss
  priority: number;
}

export interface AndonRawSlotStatus {
  locationId: number;
  locationCode: string;
  name: string;
  positionIndex?: number | null;
  hasCart: boolean;
  cartCode?: string | null;
  modelCode?: string | null;
  modelName?: string | null;
}

export interface AndonRawMaterialResponse {
  demands: AndonRawMaterialDemand[];
  rawSlots: AndonRawSlotStatus[];
}
