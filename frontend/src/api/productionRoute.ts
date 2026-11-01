import axiosInstance from './axiosInstance';
import type {
  AvailableMachine,
  ProductionRoute,
  ProductionRouteCreate,
  ProductionRouteUpdate,
} from '@/types/productionRoute';

export const getProductionRoutesApi = async (params?: {
  item_id?: number;
  is_active?: boolean;
}): Promise<ProductionRoute[]> => {
  const response = await axiosInstance.get<ProductionRoute[]>(
    '/api/v1/production/routes',
    { params },
  );
  return response.data;
};

export const getProductionRouteDetailApi = async (
  routeId: number,
): Promise<ProductionRoute> => {
  const response = await axiosInstance.get<ProductionRoute>(
    `/api/v1/production/routes/${routeId}`,
  );
  return response.data;
};

export const createProductionRouteApi = async (
  payload: ProductionRouteCreate,
): Promise<ProductionRoute> => {
  const response = await axiosInstance.post<ProductionRoute>(
    '/api/v1/production/routes',
    payload,
  );
  return response.data;
};

export const updateProductionRouteApi = async (
  routeId: number,
  payload: ProductionRouteUpdate,
): Promise<ProductionRoute> => {
  const response = await axiosInstance.put<ProductionRoute>(
    `/api/v1/production/routes/${routeId}`,
    payload,
  );
  return response.data;
};

export const activateProductionRouteApi = async (
  routeId: number,
): Promise<ProductionRoute> => {
  const response = await axiosInstance.patch<ProductionRoute>(
    `/api/v1/production/routes/${routeId}/activate`,
  );
  return response.data;
};

export const deleteProductionRouteApi = async (
  routeId: number,
): Promise<void> => {
  await axiosInstance.delete(`/api/v1/production/routes/${routeId}`);
};

export const getAvailableMachinesApi = async (): Promise<AvailableMachine[]> => {
  const response = await axiosInstance.get<AvailableMachine[]>(
    '/api/v1/production/machines',
  );
  return response.data;
};
