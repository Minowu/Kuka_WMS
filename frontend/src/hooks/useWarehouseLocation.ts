import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  getAllItemStockByZoneApi,
  getAllLocationsByZoneApi,
  listStorageLocationsApi,
  listStorageRelocateCommandsApi,
  relocateStorageStockApi,
} from '@/api/warehouseLocation';
import { useZoneMapStatus } from '@/hooks/useWarehouseMap';
import type {
  LocationStockLabel,
  StorageLocation,
  StorageRelocateCommand,
  StorageRelocateInput,
  StorageRelocateResult,
  StorageStockStatus,
  WarehouseLocation,
} from '@/types/warehouseLocation';
import { ApiErrorResponse } from '@/types/apiError';

export const warehouseLocationsQueryKey = (warehouseId: number) =>
  ['warehouse_locations', warehouseId] as const;
export const itemStockByZoneQueryKey = (warehouseId: number) =>
  ['item_stock_by_zone', warehouseId] as const;
export const locationStockLabelsQueryKey = (warehouseId: number) =>
  ['location_stock_labels', warehouseId] as const;
export const storageLocationsQueryKey = (
  warehouseId: number,
  stockStatus: StorageStockStatus,
) => ['storage_locations', warehouseId, stockStatus] as const;
export const storageRelocateCommandsQueryKey = (warehouseId: number) =>
  ['storage_relocate_commands', warehouseId] as const;

export const useLocationsByZone = (warehouseId: number) => {
  return useQuery<WarehouseLocation[], AxiosError<ApiErrorResponse>>({
    queryKey: warehouseLocationsQueryKey(warehouseId),
    queryFn: () => getAllLocationsByZoneApi(warehouseId),
    enabled: warehouseId > 0,
    staleTime: 2 * 60 * 1000,
  });
};

export const useLocationByCodeMap = (warehouseId: number) => {
  const query = useZoneMapStatus(warehouseId);

  const locationByCode = useMemo(() => {
    const map: Record<string, WarehouseLocation> = {};
    for (const loc of query.data?.locations ?? []) {
      map[loc.location_code] = {
        id: loc.id,
        location_code: loc.location_code,
        node_name: null,
        zone_id: warehouseId,
        row: loc.row ?? null,
        column: loc.column ?? null,
        level: loc.level ?? null,
        status: loc.status ?? null,
        is_active: true,
        bin: (loc as any).location_name ?? null,
        capacity: null,
        created_at: '',
        updated_at: '',
      };
    }
    return map;
  }, [query.data, warehouseId]);

  return { ...query, locationByCode };
};


export const useItemStockByZone = (warehouseId: number) => {
  return useQuery({
    queryKey: itemStockByZoneQueryKey(warehouseId),
    queryFn: () => getAllItemStockByZoneApi(warehouseId),
    enabled: warehouseId > 0,
    staleTime: 30 * 1000,
    refetchOnMount: "always",
  });
};

export const useLocationStockLabels = (warehouseId: number) => {
  const query = useZoneMapStatus(warehouseId);

  const labelByCode = useMemo(() => {
    const map = new Map<string, LocationStockLabel>();
    for (const cell of query.data?.locations ?? []) {
      let qty = 0;
      for (const item of cell.item_stock ?? []) {
        qty += Number(item.quantity) || 0;
      }
      map.set(cell.location_code, {
        location_id: cell.id,
        location_code: cell.location_code,
        is_empty: (cell.item_stock ?? []).length === 0,
        display_status: cell.status,
        product_sku: cell.item_stock?.[0]?.sku ?? null,
        product_name: cell.item_stock?.[0]?.sku ?? null,
        bin: (cell as any).location_name ?? null,
        location_type: null,
        quantity: qty,
        line_count: (cell.item_stock ?? []).length,
      });
    }
    return map;
  }, [query.data]);

  return { ...query, data: Array.from(labelByCode.values()), labelByCode };
};

export const useStockedLocationIds = (warehouseId: number) => {
  const locationsQuery = useLocationsByZone(warehouseId);
  const stockQuery = useItemStockByZone(warehouseId);

  const stockedLocationIds = useMemo(() => {
    const ids = new Set<number>();
    for (const row of stockQuery.data ?? []) {
      if (Number(row.quantity) > 0) {
        ids.add(row.location_id);
      }
    }
    return ids;
  }, [stockQuery.data]);

  return {
    ...stockQuery,
    stockedLocationIds,
    isLoading: stockQuery.isLoading || locationsQuery.isLoading,
  };
};

export const useStorageLocations = (
  warehouseId: number,
  stockStatus: StorageStockStatus,
  enabled = true,
) => {
  return useQuery<StorageLocation[], AxiosError<ApiErrorResponse>>({
    queryKey: storageLocationsQueryKey(warehouseId, stockStatus),
    queryFn: async () => {
      const res = await listStorageLocationsApi({
        warehouseId,
        stockStatus,
        limit: 1000,
      });
      return res.locations;
    },
    enabled: enabled && warehouseId > 0,
    staleTime: 30 * 1000,
  });
};

export const useStorageRelocateCommands = (warehouseId: number, enabled = true) => {
  return useQuery<StorageRelocateCommand[], AxiosError<ApiErrorResponse>>({
    queryKey: storageRelocateCommandsQueryKey(warehouseId),
    queryFn: async () => {
      const res = await listStorageRelocateCommandsApi({
        warehouseId,
        limit: 50,
      });
      return res.commands;
    },
    enabled: enabled && warehouseId > 0,
    staleTime: 15 * 1000,
  });
};

export const useRelocateStorageStock = () => {
  const queryClient = useQueryClient();

  return useMutation<
    StorageRelocateResult,
    AxiosError<ApiErrorResponse>,
    StorageRelocateInput
  >({
    mutationFn: relocateStorageStockApi,
    onSuccess: (_data, variables) => {
      const { zone_id: warehouseId } = variables;
      void queryClient.invalidateQueries({
        queryKey: storageLocationsQueryKey(warehouseId, 'occupied'),
      });
      void queryClient.invalidateQueries({
        queryKey: storageLocationsQueryKey(warehouseId, 'empty'),
      });
      void queryClient.invalidateQueries({
        queryKey: storageRelocateCommandsQueryKey(warehouseId),
      });
      void queryClient.invalidateQueries({
        queryKey: locationStockLabelsQueryKey(warehouseId),
      });
      void queryClient.invalidateQueries({
        queryKey: itemStockByZoneQueryKey(warehouseId),
      });
      void queryClient.invalidateQueries({
        queryKey: warehouseLocationsQueryKey(warehouseId),
      });
    },
  });
};

export type ShelfOccupancy = 'empty' | 'occupied' | 'unsynced';

export function getShelfOccupancy(
  locationCode: string,
  locationByCode: Record<string, WarehouseLocation>,
  stockedLocationIds: Set<number>,
): ShelfOccupancy {
  const location = locationByCode[locationCode];
  if (!location) return 'unsynced';
  return stockedLocationIds.has(location.id) ? 'occupied' : 'empty';
}
