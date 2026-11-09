import axiosInstance from './axiosInstance';

export interface RackManagementItem {
  id: number;
  container_code: string;
  item_id: number | null;
  item_sku: string | null;
  item_name: string | null;
  location_id: number | null;
  location_code: string | null;
  location_label: string | null;
  location_name: string | null;
  location_type: string | null;
  machine_code: string | null;
  destination_location_id: number | null;
  destination_location_name: string | null;
  quantity: number;
  current_stage_level: number;
  status: string;
  is_active: boolean;
  is_locked: boolean;
  locked_by_mission_code: string | null;
  active_request_code: string | null;
  active_request_status: string | null;
  can_modify: boolean;
  block_reason: string | null;
  can_relocate?: boolean;
  relocate_block_reason?: string | null;
  allowed_location_ids?: number[];
  fleet_registered: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface RackUpdateLocationPayload {
  location_id: number;
}

export interface RackActionResponse {
  success: boolean;
  message: string;
  rack?: RackManagementItem | null;
}

export const getProductionRacksApi = async (params?: {
  include_inactive?: boolean;
  search?: string;
}): Promise<RackManagementItem[]> => {
  const response = await axiosInstance.get<RackManagementItem[]>(
    '/api/v1/production/racks',
    { params },
  );
  return response.data;
};

export const removeProductionRackApi = async (
  rackId: number,
): Promise<RackActionResponse> => {
  const response = await axiosInstance.delete<RackActionResponse>(
    `/api/v1/production/racks/${rackId}`,
  );
  return response.data;
};

export const updateProductionRackLocationApi = async (
  rackId: number,
  payload: RackUpdateLocationPayload,
): Promise<RackActionResponse> => {
  const response = await axiosInstance.put<RackActionResponse>(
    `/api/v1/production/racks/${rackId}/location`,
    payload,
  );
  return response.data;
};
