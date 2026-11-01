import axiosInstance from './axiosInstance';
import type { AndonRawMaterialResponse } from '@/types/andon';

export const getRawMaterialAndonQueueApi = async (warehouseId?: number): Promise<AndonRawMaterialResponse> => {
  const params: Record<string, any> = {};
  if (warehouseId) params.warehouse_id = warehouseId;

  const response = await axiosInstance.get<any>('/api/v1/production/andon/raw-material-queue', {
    params,
  });

  const raw = response.data;
  return {
    demands: (raw.demands || []).map((d: any) => ({
      id: d.id,
      requestCode: d.request_code,
      modelCode: d.model_code,
      modelName: d.model_name,
      machineCode: d.machine_code,
      machineName: d.machine_name,
      positionIndex: d.position_index,
      destinationLocationCode: d.destination_location_code,
      calledAt: d.called_at,
      priority: d.priority ?? 10,
    })),
    rawSlots: (raw.raw_slots || []).map((s: any) => ({
      locationId: s.location_id,
      locationCode: s.location_code,
      name: s.name,
      positionIndex: s.position_index,
      hasCart: s.has_cart,
      cartCode: s.cart_code,
      modelCode: s.model_code,
      modelName: s.model_name,
    })),
  };
};
