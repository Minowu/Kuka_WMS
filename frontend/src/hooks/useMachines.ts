import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getMachinesApi,
  createMachineApi,
  updateMachineApi,
  deleteMachineApi,
  getStationCatalogApi,
  getAvailableMapNodesApi,
  createStationLocationApi,
  updateStationLocationApi,
  deleteStationLocationApi,
  getUserLocationsApi,
  updateUserLocationsApi,
} from '@/api/machine';
import type {
  MachineCreateInput,
  MachineUpdateInput,
  StationLocationCreateInput,
  StationLocationUpdateInput,
} from '@/types/machine';

export const useMachines = () => {
  return useQuery({
    queryKey: ['machines'],
    queryFn: getMachinesApi,
    staleTime: 60 * 1000,
  });
};

export const useCreateMachine = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MachineCreateInput) => createMachineApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
    },
  });
};

export const useUpdateMachine = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MachineUpdateInput }) =>
      updateMachineApi(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
    },
  });
};

export const useDeleteMachine = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteMachineApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
    },
  });
};

export const useStationCatalog = () => {
  return useQuery({
    queryKey: ['stationCatalog'],
    queryFn: getStationCatalogApi,
    staleTime: 30 * 1000,
  });
};

export const useAvailableNodes = () => {
  return useQuery({
    queryKey: ['availableMapNodes'],
    queryFn: getAvailableMapNodesApi,
    staleTime: 5 * 60 * 1000,
  });
};

export const useCreateStationLocation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: StationLocationCreateInput) => createStationLocationApi(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stationCatalog'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
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
    },
  });
};

export const useUserLocations = (userId?: number) => {
  return useQuery({
    queryKey: ['userLocations', userId],
    queryFn: () => (userId ? getUserLocationsApi(userId) : Promise.resolve([])),
    enabled: !!userId,
  });
};

export const useUpdateUserLocations = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, locationIds }: { userId: number; locationIds: number[] }) =>
      updateUserLocationsApi(userId, locationIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['userLocations', variables.userId] });
    },
  });
};
