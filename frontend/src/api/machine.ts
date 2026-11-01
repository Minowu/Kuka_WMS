import axiosInstance from './axiosInstance';
import type {
  MachineItem,
  MachineCreateInput,
  MachineUpdateInput,
} from '@/types/machine';

/**
 * QUẢN LÝ MÁY CNC & VỊ TRÍ ĐỖ (POS1..3)
 */
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

/**
 * PHÂN QUYỀN VỊ TRÍ CHO NGƯỜI DÙNG / OPERATOR
 */
export const getUserLocationsApi = async (userId: number): Promise<number[]> => {
  const response = await axiosInstance.get<number[]>(`/api/v1/production/users/${userId}/locations`);
  return response.data;
};

export const updateUserLocationsApi = async (userId: number, locationIds: number[]): Promise<number[]> => {
  const response = await axiosInstance.put<number[]>(`/api/v1/production/users/${userId}/locations`, locationIds);
  return response.data;
};
