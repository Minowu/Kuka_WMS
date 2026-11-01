import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  activateProductionRouteApi,
  createProductionRouteApi,
  deleteProductionRouteApi,
  getAvailableMachinesApi,
  getProductionRouteDetailApi,
  getProductionRoutesApi,
  updateProductionRouteApi,
} from '@/api/productionRoute';
import type {
  ProductionRouteCreate,
  ProductionRouteUpdate,
} from '@/types/productionRoute';

export const useProductionRoutes = (params?: {
  item_id?: number;
  is_active?: boolean;
}) => {
  return useQuery({
    queryKey: ['production_routes', params?.item_id, params?.is_active],
    queryFn: () => getProductionRoutesApi(params),
  });
};

export const useProductionRouteDetail = (routeId?: number) => {
  return useQuery({
    queryKey: ['production_route_detail', routeId],
    queryFn: () => getProductionRouteDetailApi(routeId!),
    enabled: !!routeId,
  });
};

export const useAvailableMachines = () => {
  return useQuery({
    queryKey: ['production_machines'],
    queryFn: () => getAvailableMachinesApi(),
    staleTime: 60 * 1000,
  });
};

export const useCreateProductionRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductionRouteCreate) =>
      createProductionRouteApi(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production_routes'] });
    },
  });
};

export const useUpdateProductionRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      routeId,
      payload,
    }: {
      routeId: number;
      payload: ProductionRouteUpdate;
    }) => updateProductionRouteApi(routeId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['production_routes'] });
      queryClient.invalidateQueries({
        queryKey: ['production_route_detail', variables.routeId],
      });
    },
  });
};

export const useActivateProductionRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (routeId: number) => activateProductionRouteApi(routeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production_routes'] });
    },
  });
};

export const useDeleteProductionRoute = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (routeId: number) => deleteProductionRouteApi(routeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['production_routes'] });
    },
  });
};
