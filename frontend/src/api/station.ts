import axiosInstance from './axiosInstance';
import type {
  StationCatalogResponse,
  AvailableMapNode,
  StationCatalogItem,
  StationLocationCreateInput,
  StationLocationUpdateInput,
} from '@/types/station';

/**
 * 1. TẢI TOÀN BỘ HIỆN TRẠNG PHÂN KHU XƯỞNG HỢP NHẤT
 * (Cấp phôi, Máy CNC 1..3 slot, Trạm rửa, Bãi đệm xe rỗng)
 */
export const getStationCatalogApi = async (): Promise<StationCatalogResponse> => {
  const response = await axiosInstance.get<StationCatalogResponse>('/api/v1/production/stations/catalog');
  return response.data;
};

/**
 * 2. LẤY DANH SÁCH NODE BẢN ĐỒ THỰC TẾ (GROUND TRUTH TỪ DB / MAP KUKA)
 * Tuyệt đối không dùng mảng fix cứng; backend query trực tiếp từ DB map nodes.
 */
export const getAvailableMapNodesApi = async (): Promise<AvailableMapNode[]> => {
  const response = await axiosInstance.get<AvailableMapNode[]>('/api/v1/production/map/available-nodes');
  return response.data;
};

/**
 * 3. QUẢN LÝ ĐIỂM ĐỖ ĐỘC LẬP (Ô CẤP PHÔI, TRẠM RỬA, BÃI ĐỆM)
 */
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
    if (err?.response?.status === 404) {
      await axiosInstance.delete(`/api/v1/locations/${id}`);
    } else {
      throw err;
    }
  }
};
