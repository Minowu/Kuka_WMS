import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getMachinesApi,
  createMachineApi,
  updateMachineApi,
  deleteMachineApi,
  getUserLocationsApi,
  updateUserLocationsApi,
} from '@/api/machine';
import type {
  MachineCreateInput,
  MachineUpdateInput,
} from '@/types/machine';

/**
 * Hooks quản trị Máy CNC thuần túy
 */
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
      queryClient.invalidateQueries({ queryKey: ['availableMapNodes'] });
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
      queryClient.invalidateQueries({ queryKey: ['availableMapNodes'] });
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
      queryClient.invalidateQueries({ queryKey: ['availableMapNodes'] });
    },
  });
};

/**
 * Hooks phân quyền vị trí thao tác cho User / PDA Operator
 */
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
