import axiosInstance from './axiosInstance';
import type {
  PartModel,
  RawMaterialPosition,
  CncMachineStation,
  WashingSlot,
} from '@/types/pda';

// 1. Fetch Master Data & Current Floor State
export const getPdaModelsApi = async (): Promise<PartModel[]> => {
  const response = await axiosInstance.get<PartModel[]>('/api/v1/production/pda/models');
  return response.data;
};

export const getPdaRawMaterialsApi = async (): Promise<RawMaterialPosition[]> => {
  const response = await axiosInstance.get<any[]>('/api/v1/production/pda/raw-materials');
  return (response.data || []).map((r) => ({
    id: r.id,
    locationId: r.location_id ?? r.locationId,
    name: r.name,
    hasRack: r.has_rack ?? r.hasRack ?? false,
    currentRackId: r.current_rack_id ?? r.currentRackId,
    currentModel: r.current_model ?? r.currentModel,
  }));
};

export const getPdaCncStationsApi = async (): Promise<CncMachineStation[]> => {
  const response = await axiosInstance.get<any[]>('/api/v1/production/pda/cnc-stations');
  return (response.data || []).map((s) => ({
    id: s.id,
    locationId: s.location_id ?? s.locationId,
    machineCode: s.machine_code ?? s.machineCode,
    positionIndex: s.position_index ?? s.positionIndex,
    name: s.name,
    assignedStageLevel: s.assigned_stage_level ?? s.assignedStageLevel ?? 1,
    stageName: s.stage_name ?? s.stageName ?? `Công đoạn Level ${s.assigned_stage_level ?? 1}`,
    status: s.status,
    callingModel: s.calling_model ?? s.callingModel,
    callingTaskCode: s.calling_mission_code ?? s.calling_task_code ?? s.callingTaskCode,
    supportedModels: (s.supported_models || s.supportedModels || []).map((m: any) => ({
      itemId: m.item_id ?? m.itemId,
      modelCode: m.model_code ?? m.modelCode,
      modelName: m.model_name ?? m.modelName,
      stageLevel: m.stage_level ?? m.stageLevel,
      stageName: m.stage_name ?? m.stageName,
      inputStageLevel: m.input_stage_level ?? m.inputStageLevel,
    })),
    currentRack: s.current_rack
      ? {
          rackId: s.current_rack.rack_id ?? s.current_rack.rackId,
          model: s.current_rack.model,
          level: s.current_rack.level,
          startedAt: s.current_rack.started_at ?? s.current_rack.startedAt,
        }
      : s.currentRack ?? null,
  }));
};

export const getPdaWashingSlotsApi = async (): Promise<WashingSlot[]> => {
  const response = await axiosInstance.get<any[]>('/api/v1/production/pda/washing-slots');
  return (response.data || []).map((w) => ({
    id: w.id,
    locationId: w.location_id ?? w.locationId,
    code: w.code,
    name: w.name,
    status: w.status,
    currentRack: w.current_rack
      ? {
          rackId: w.current_rack.rack_id ?? w.current_rack.rackId,
          model: w.current_rack.model,
          fromStation: w.current_rack.from_station ?? w.current_rack.fromStation,
          arrivedAt: w.current_rack.arrived_at ?? w.current_rack.arrivedAt,
        }
      : w.currentRack ?? null,
  }));
};

// 2. Production Actions
export interface RegisterRawMaterialPayload {
  location_id: number;
  item_id: number;
  container_code: string;
  quantity?: number;
  lot_number?: string;
}

export const registerRawMaterialApi = async (payload: RegisterRawMaterialPayload) => {
  const response = await axiosInstance.post(
    '/api/v1/production/racks/register-raw-material',
    payload
  );
  return response.data;
};

export interface CallMaterialPayload {
  destination_location_id: number;
  item_id: number;
  priority?: number;
}

export const callMaterialToCncApi = async (payload: CallMaterialPayload) => {
  const response = await axiosInstance.post(
    '/api/v1/production/dispatch/call-material',
    payload
  );
  return response.data;
};

export interface CompleteStagePayload {
  container_code?: string;
  location_id?: number;
  notes?: string;
}

export const completeMachiningStageApi = async (payload: CompleteStagePayload) => {
  const response = await axiosInstance.post(
    '/api/v1/production/dispatch/complete-stage',
    payload
  );
  return response.data;
};

export interface ReturnEmptyCartPayload {
  container_code: string;
}

export const returnEmptyCartFromWashingApi = async (payload: ReturnEmptyCartPayload) => {
  const response = await axiosInstance.post(
    '/api/v1/production/dispatch/return-empty-cart-from-washing',
    payload
  );
  return response.data;
};
