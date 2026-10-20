import axiosInstance from './axiosInstance';
import type {
  MachineItem,
  MachineCreateInput,
  MachineUpdateInput,
  StationCatalogResponse,
  AvailableMapNode,
  StationCatalogItem,
  StationLocationCreateInput,
  StationLocationUpdateInput,
} from '@/types/machine';

// 16 Node kệ/điểm đỗ vận hành thực tế (functionType == 2) từ map_CNC001_CNC001_28s.json
export const FALLBACK_MAP_NODES: AvailableMapNode[] = [
  { node_number: 4, node_label: '4', map_x: 178513, map_y: 77500, function_type: 2 },
  { node_number: 17, node_label: '17', map_x: 179713, map_y: 83800, function_type: 2 },
  { node_number: 18, node_label: '18', map_x: 178513, map_y: 83800, function_type: 2 },
  { node_number: 20, node_label: '20', map_x: 180913, map_y: 83800, function_type: 2 },
  { node_number: 23, node_label: '23', map_x: 182113, map_y: 83800, function_type: 2 },
  { node_number: 24, node_label: '24', map_x: 183313, map_y: 83800, function_type: 2 },
  { node_number: 25, node_label: '25', map_x: 184513, map_y: 83800, function_type: 2 },
  { node_number: 26, node_label: '26', map_x: 185713, map_y: 83800, function_type: 2 },
  { node_number: 50, node_label: '50', map_x: 179713, map_y: 77500, function_type: 2 },
  { node_number: 51, node_label: '51', map_x: 180913, map_y: 77500, function_type: 2 },
  { node_number: 127, node_label: '127', map_x: 171000, map_y: 41700, function_type: 2 },
  { node_number: 128, node_label: '128', map_x: 172500, map_y: 41700, function_type: 2 },
  { node_number: 129, node_label: '129', map_x: 174000, map_y: 41700, function_type: 2 },
  { node_number: 130, node_label: '130', map_x: 175500, map_y: 41700, function_type: 2 },
  { node_number: 216, node_label: '216', map_x: 164249, map_y: 52600, function_type: 2 },
  { node_number: 249, node_label: '249', map_x: 156049, map_y: 52600, function_type: 2 },
];


export const getMachinesApi = async (): Promise<MachineItem[]> => {
  const response = await axiosInstance.get<MachineItem[]>('/api/v1/production/machines');
  return response.data;
};

export const createMachineApi = async (data: MachineCreateInput): Promise<MachineItem> => {
  const response = await axiosInstance.post<MachineItem>('/api/v1/production/machines', data);
  return response.data;
};

export const updateMachineApi = async (id: number, data: MachineUpdateInput): Promise<MachineItem> => {
  const response = await axiosInstance.put<MachineItem>(`/api/v1/production/machines/${id}`, data);
  return response.data;
};

export const deleteMachineApi = async (id: number): Promise<void> => {
  await axiosInstance.delete(`/api/v1/production/machines/${id}`);
};

export const getStationCatalogApi = async (): Promise<StationCatalogResponse> => {
  const response = await axiosInstance.get<StationCatalogResponse>('/api/v1/production/stations/catalog');
  return response.data;
};

export const getAvailableMapNodesApi = async (): Promise<AvailableMapNode[]> => {
  try {
    const response = await axiosInstance.get<AvailableMapNode[]>('/api/v1/production/map/available-nodes');
    if (Array.isArray(response.data) && response.data.length > 0) {
      return response.data;
    }
    return FALLBACK_MAP_NODES;
  } catch (error) {
    console.warn('Cannot fetch available nodes from server, using fallback map nodes:', error);
    return FALLBACK_MAP_NODES;
  }
};

export const createStationLocationApi = async (data: StationLocationCreateInput): Promise<StationCatalogItem> => {
  const response = await axiosInstance.post<StationCatalogItem>('/api/v1/production/stations/locations', data);
  return response.data;
};

export const updateStationLocationApi = async (
  id: number,
  data: StationLocationUpdateInput
): Promise<StationCatalogItem> => {
  const response = await axiosInstance.put<StationCatalogItem>(`/api/v1/production/stations/locations/${id}`, data);
  return response.data;
};

export const deleteStationLocationApi = async (id: number): Promise<void> => {
  try {
    await axiosInstance.delete(`/api/v1/production/stations/locations/${id}`);
  } catch (err: any) {
    // Fallback to general location delete endpoint if station-specific delete returns 404
    if (err?.response?.status === 404) {
      await axiosInstance.delete(`/api/v1/locations/${id}`);
    } else {
      throw err;
    }
  }
};

export const getUserLocationsApi = async (userId: number): Promise<number[]> => {
  const response = await axiosInstance.get<number[]>(`/api/v1/production/users/${userId}/locations`);
  return response.data;
};

export const updateUserLocationsApi = async (userId: number, locationIds: number[]): Promise<number[]> => {
  const response = await axiosInstance.put<number[]>(`/api/v1/production/users/${userId}/locations`, locationIds);
  return response.data;
};
