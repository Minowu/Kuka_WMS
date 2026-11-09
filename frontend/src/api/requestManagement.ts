import axiosInstance from './axiosInstance';

export interface TransportRequestManagementItem {
  id: number;
  request_code: string;
  request_type: string;
  status: string;
  priority: number;
  item_id: number | null;
  item_sku: string | null;
  item_name: string | null;
  required_stage_level: number;
  target_stage_level: number | null;
  container_id: number | null;
  container_code: string | null;
  source_location_id: number | null;
  source_location_code: string | null;
  source_location_name: string | null;
  source_location_label: string | null;
  source_location_type: string | null;
  source_machine_code: string | null;
  destination_location_id: number | null;
  destination_location_code: string | null;
  destination_location_name: string | null;
  destination_location_label: string | null;
  destination_location_type: string | null;
  destination_machine_code: string | null;
  queue_type: string | null;
  queue_status: string | null;
  mission_code: string | null;
  fleet_task_status: string | null;
  robot_id: string | null;
  created_by: number | null;
  created_by_username: string | null;
  created_by_full_name: string | null;
  can_cancel: boolean;
  cancel_block_reason: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface TransportRequestCancelResponse {
  success: boolean;
  message: string;
  request?: TransportRequestManagementItem | null;
}

export const getProductionRequestsApi = async (params?: {
  include_history?: boolean;
  search?: string;
}): Promise<TransportRequestManagementItem[]> => {
  const response = await axiosInstance.get<TransportRequestManagementItem[]>(
    '/api/v1/production/requests',
    { params },
  );
  return response.data;
};

export const cancelProductionRequestApi = async (
  requestId: number,
): Promise<TransportRequestCancelResponse> => {
  const response = await axiosInstance.post<TransportRequestCancelResponse>(
    `/api/v1/production/requests/${requestId}/cancel`,
  );
  return response.data;
};
