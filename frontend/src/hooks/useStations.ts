import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getStationCatalogApi,
  getAvailableMapNodesApi,
  createStationLocationApi,
  updateStationLocationApi,
  deleteStationLocationApi,
} from '@/api/station';
import type {
  StationLocationCreateInput,
  StationLocationUpdateInput,
} from '@/types/station';

/**
 * 1. Hook tải toàn bộ danh mục phân khu xưởng (3 Tab: Cấp phôi | Máy CNC | Rửa & Đệm)
 */
export const useStationCatalog = () => {
  return useQuery({
    queryKey: ['stationCatalog'],
    queryFn: getStationCatalogApi,
    staleTime: 0,
  });
};

/**
 * 2. Hook lấy danh sách Node bản đồ KUKA thực tế (Fetch từ DB backend, không fix cứng)
 */
export const useAvailableNodes = () => {
  return useQuery({
    queryKey: ['availableMapNodes'],
    queryFn: getAvailableMapNodesApi,
    staleTime: 0,
  });
};

/**
 * 3. Hooks quản trị điểm đỗ độc lập (Ô phôi, Trạm rửa, Bãi đệm xe rỗng)
 */
export const useCreateStationLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: StationLocationCreateInput) => createStationLocationApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['availableMapNodes'] });
    },
  });
};

export const useUpdateStationLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: StationLocationUpdateInput }) =>
      updateStationLocationApi(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['availableMapNodes'] });
    },
  });
};

export const useDeleteStationLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteStationLocationApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['availableMapNodes'] });
    },
  });
};
