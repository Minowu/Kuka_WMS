import { useCallback } from 'react';
import {
  useQuery,
  useQueries,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query';

import { AxiosError } from 'axios';
import {
  DEFAULT_MAP_LOCATION_TYPE,
  getActiveMapApi,
  getActiveMapMetadataApi,
  getInboundBufferMapViewApi,
  getInboundBufferPointsApi,
  importMapApi,
  type MapLocationTypeParam,
} from '@/api/warehouseMap';
import type {
  InboundBufferMapView,
  InboundBufferPointsResponse,
  WarehouseMapMetadata,
} from '@/types/warehouseMap';
import type { ApiErrorResponse } from '@/types/apiError';
import {
  getActiveWarehouseMapApi,
  getFullLocationsApi,
  getLocationsByLogicApi,
  importWarehouseMapApi,
  previewWarehouseMapImportApi,
  downloadActiveMapApi,
  getLocationDetailByIdApi,
  getZoneMapLayoutApi,
  getZoneMapStatusApi,
} from '@/api/warehouseMap';
import type {
  MapData,
  MapRemapEntry,
  FullLocationDetail,
  FullLocationsResponse,
  WarehouseMapImportResult,
  WarehouseLocationItemStockDetail,
  ZoneMapLayoutNode,
  ZoneMapLayoutResponse,
} from '@/types/warehouseMap';
import { LIVE_QUERY_OPTIONS } from '@/utils/liveQueryOptions';
import type { OutboundLocationLogicType } from '@/utils/outboundLocationLogic';

export const useActiveWarehouseMap = (warehouseId: number) => {
  return useQuery<MapData, AxiosError<ApiErrorResponse>>({
    queryKey: ['warehouse-map', warehouseId],
    queryFn: () => getActiveWarehouseMapApi(warehouseId),
    enabled: warehouseId > 0,
    ...LIVE_QUERY_OPTIONS,
  });
};

export const useFullLocations = (warehouseId: number) => {
  return useQuery<FullLocationsResponse, AxiosError<ApiErrorResponse>>({
    queryKey: ['full-locations', warehouseId],
    queryFn: () => getFullLocationsApi(warehouseId),
    enabled: warehouseId > 0,
    ...LIVE_QUERY_OPTIONS,
  });
};

export const useInboundBufferLocations = (
  warehouseId: number,
  enabled = true,
) => {
  return useQuery({
    queryKey: ['inbound-buffer-locations', warehouseId],
    queryFn: () => getLocationsByLogicApi(warehouseId, 'inbound_buffer'),
    enabled: enabled && warehouseId > 0,
    ...LIVE_QUERY_OPTIONS,
  });
};

export const useOutboundBufferLocations = (
  warehouseId: number,
  logicType: OutboundLocationLogicType = 'outbound_buffer',
  enabled = true,
) => {
  return useQuery({
    queryKey: ['outbound-buffer-locations', warehouseId, logicType],
    queryFn: () => getLocationsByLogicApi(warehouseId, logicType),
    enabled: enabled && warehouseId > 0,
    ...LIVE_QUERY_OPTIONS,
  });
};

export const useStorageAreaLocations = (
  warehouseId: number,
  enabled = true,
) => {
  return useQuery({
    queryKey: ['storage-area-locations', warehouseId],
    queryFn: () => getLocationsByLogicApi(warehouseId, 'storage_area'),
    enabled: enabled && warehouseId > 0,
    ...LIVE_QUERY_OPTIONS,
  });
};

interface ImportWarehouseMapVariables {
  warehouseId: number;
  file: File;
  remap?: MapRemapEntry[];
  zoneId?: number;
}

/** Dry run the import so the operator can review before anything is written. */
export const usePreviewWarehouseMapImport = () => {
  return useMutation<
    WarehouseMapImportResult,
    AxiosError<ApiErrorResponse>,
    ImportWarehouseMapVariables
  >({
    mutationFn: ({ warehouseId, file, remap, zoneId }) =>
      previewWarehouseMapImportApi(warehouseId, file, remap, zoneId),
  });
};

export const useImportWarehouseMap = () => {
  const queryClient = useQueryClient();
  return useMutation<
    WarehouseMapImportResult,
    AxiosError<ApiErrorResponse>,
    ImportWarehouseMapVariables
  >({
    mutationFn: ({ warehouseId, file, remap, zoneId }) =>
      importWarehouseMapApi(warehouseId, file, remap, zoneId),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['warehouse-map', variables.warehouseId],
      });
      queryClient.invalidateQueries({
        queryKey: ['full-locations', variables.warehouseId],
      });
    },
  });
};

export const useDownloadWarehouseMap = () => {
  return useMutation<
    void,
    AxiosError<ApiErrorResponse>,
    { warehouseId: number }
  >({
    mutationFn: async ({ warehouseId }) => {
      const { blob, filename } = await downloadActiveMapApi(warehouseId);
      const isJson = blob.type.includes('json') || filename?.endsWith('.json');
      const fallbackName = `warehouse-map-${warehouseId}${isJson ? '.json' : '.zip'}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename || fallbackName;
      anchor.click();
      URL.revokeObjectURL(url);
    },
  });
};

export const useLocationDetail = (
  locationId: number | undefined,
  refreshToken = 0,
) => {
  return useQuery<
    WarehouseLocationItemStockDetail,
    AxiosError<ApiErrorResponse>
  >({
    queryKey: ['location-detail', locationId, refreshToken],
    queryFn: () => getLocationDetailByIdApi(locationId as number),
    enabled: !!locationId && locationId > 0,
    ...LIVE_QUERY_OPTIONS,
  });
};


export const warehouseMapQueryKey = (warehouseId: number) => ['warehouse_map', warehouseId] as const;
export const warehouseMapMetadataQueryKey = (warehouseId: number) =>
  ['warehouse_map_metadata', warehouseId] as const;
function locationIdsKey(locationIds?: number[]) {
  if (!locationIds || locationIds.length === 0) return 'all';
  return [...locationIds].sort((a, b) => a - b).join(',');
}

export const inboundBufferPointsQueryKey = (
  warehouseId: number,
  locationType: MapLocationTypeParam = DEFAULT_MAP_LOCATION_TYPE,
  locationIds?: number[],
) =>
  [
    'inbound_buffer_points',
    warehouseId,
    locationType,
    locationIdsKey(locationIds),
  ] as const;
export const inboundBufferMapViewQueryKey = (
  warehouseId: number,
  locationType: MapLocationTypeParam = DEFAULT_MAP_LOCATION_TYPE,
  locationIds?: number[],
) =>
  [
    'inbound_buffer_map_view',
    warehouseId,
    locationType,
    locationIdsKey(locationIds),
  ] as const;

export const useActiveMap = (warehouseId: number) => {
  return useQuery<MapData, AxiosError<ApiErrorResponse>>({
    queryKey: warehouseMapQueryKey(warehouseId),
    queryFn: () => getActiveMapApi(warehouseId),
    enabled: warehouseId > 0,
    staleTime: 2 * 60 * 1000,
    retry: (failureCount, error) => {
      if (error.response?.status === 404) return false;
      return failureCount < 2;
    },
  });
};

export const useActiveMapMetadata = (warehouseId: number) => {
  return useQuery<WarehouseMapMetadata, AxiosError<ApiErrorResponse>>({
    queryKey: warehouseMapMetadataQueryKey(warehouseId),
    queryFn: () => getActiveMapMetadataApi(warehouseId),
    enabled: warehouseId > 0,
    staleTime: 2 * 60 * 1000,
    retry: (failureCount, error) => {
      if (error.response?.status === 404) return false;
      return failureCount < 2;
    },
  });
};

export const useInboundBufferPoints = (
  warehouseId: number,
  locationType: MapLocationTypeParam = DEFAULT_MAP_LOCATION_TYPE,
  locationIds?: number[],
) => {
  const hasExplicitEmptyFilter = Array.isArray(locationIds) && locationIds.length === 0;
  return useQuery<InboundBufferPointsResponse, AxiosError<ApiErrorResponse>>({
    queryKey: inboundBufferPointsQueryKey(warehouseId, locationType, locationIds),
    queryFn: () => getInboundBufferPointsApi(warehouseId, locationType, locationIds),
    enabled: warehouseId > 0 && !hasExplicitEmptyFilter,
    staleTime: 60 * 1000,
  });
};

export const useInboundBufferMapView = (
  warehouseId: number,
  locationType: MapLocationTypeParam = DEFAULT_MAP_LOCATION_TYPE,
  locationIds?: number[],
) => {
  const hasExplicitEmptyFilter = Array.isArray(locationIds) && locationIds.length === 0;
  return useQuery<InboundBufferMapView, AxiosError<ApiErrorResponse>>({
    queryKey: inboundBufferMapViewQueryKey(warehouseId, locationType, locationIds),
    queryFn: () => getInboundBufferMapViewApi(warehouseId, locationType, locationIds),
    enabled: warehouseId > 0 && !hasExplicitEmptyFilter,
    staleTime: 60 * 1000,
    retry: (failureCount, error) => {
      if (error.response?.status === 404 || error.response?.status === 422) return false;
      return failureCount < 2;
    },
  });
};

export const useZoneMapLayout = (zoneId: number) => {
  return useQuery<ZoneMapLayoutResponse, AxiosError<ApiErrorResponse>>({
    queryKey: ['zone_map_layout', zoneId],
    queryFn: () => getZoneMapLayoutApi(zoneId),
    enabled: zoneId > 0,
    staleTime: 5 * 60 * 1000,
    retry: (failureCount, error) => {
      if (error.response?.status === 404) return false;
      return failureCount < 2;
    },
  });
};

export const useZoneMapStatus = (zoneId: number) => {
  return useQuery<FullLocationsResponse, AxiosError<ApiErrorResponse>>({
    queryKey: ['zone_map_status', zoneId],
    queryFn: () => getZoneMapStatusApi(zoneId),
    enabled: zoneId > 0,
    refetchInterval: 5000, // Poll every 5 seconds for status
    staleTime: 1000,
  });
};

export type MergedZoneQueries<TItem> = {
  /** Item của mọi zone đã tải được, gộp và bỏ trùng theo location_code (zone đứng trước được giữ). */
  items: TItem[];
  /** Còn ít nhất 1 zone đang tải lần đầu. */
  isLoading: boolean;
  /** Các zone lỗi (kể cả lỗi khi polling lại mà vẫn còn data cũ). */
  failedZoneIds: number[];
};

function mergeZoneResults<TData, TItem extends { location_code: string }>(
  zoneIds: number[],
  results: UseQueryResult<TData>[],
  pickItems: (data: TData) => TItem[],
): MergedZoneQueries<TItem> {
  const seen = new Set<string>();
  const items: TItem[] = [];
  const failedZoneIds: number[] = [];
  results.forEach((result, index) => {
    if (result.isError) failedZoneIds.push(zoneIds[index]);
    if (!result.data) return;
    for (const item of pickItems(result.data)) {
      if (seen.has(item.location_code)) continue;
      seen.add(item.location_code);
      items.push(item);
    }
  });
  return {
    items,
    isLoading: results.some((r) => r.isLoading),
    failedZoneIds,
  };
}

/** Layout của nhiều zone, gọi song song rồi gộp node. Cache dùng chung với useZoneMapLayout. */
export const useZonesMapLayout = (zoneIds: number[]) => {
  const combine = useCallback(
    (results: UseQueryResult<ZoneMapLayoutResponse>[]) =>
      mergeZoneResults<ZoneMapLayoutResponse, ZoneMapLayoutNode>(zoneIds, results, (d) => d.nodes),
    [zoneIds],
  );
  return useQueries({
    queries: zoneIds.map((zoneId) => ({
      queryKey: ['zone_map_layout', zoneId],
      queryFn: () => getZoneMapLayoutApi(zoneId),
      staleTime: 5 * 60 * 1000,
      retry: (failureCount: number, error: Error) => {
        if ((error as AxiosError).response?.status === 404) return false;
        return failureCount < 2;
      },
    })),
    combine,
  });
};

/** Trạng thái location của nhiều zone, polling song song rồi gộp. Cache dùng chung với useZoneMapStatus. */
export const useZonesMapStatus = (zoneIds: number[]) => {
  const combine = useCallback(
    (results: UseQueryResult<FullLocationsResponse>[]) =>
      mergeZoneResults<FullLocationsResponse, FullLocationDetail>(zoneIds, results, (d) => d.locations),
    [zoneIds],
  );
  return useQueries({
    queries: zoneIds.map((zoneId) => ({
      queryKey: ['zone_map_status', zoneId],
      queryFn: () => getZoneMapStatusApi(zoneId),
      refetchInterval: 5000,
      staleTime: 1000,
    })),
    combine,
  });
};

export const useImportMap = () => {
  const queryClient = useQueryClient();

  return useMutation<
    WarehouseMapImportResult,
    AxiosError<ApiErrorResponse>,
    { warehouseId: number; file: File }
  >({
    mutationFn: ({ warehouseId, file }) => importMapApi(warehouseId, file),
    onSuccess: async (_data, variables) => {
      const { warehouseId } = variables;

      await Promise.all([
        queryClient.resetQueries({ queryKey: warehouseMapQueryKey(warehouseId) }),
        queryClient.resetQueries({ queryKey: warehouseMapMetadataQueryKey(warehouseId) }),
        queryClient.invalidateQueries({ queryKey: ['inbound_buffer_points', warehouseId] }),
        queryClient.invalidateQueries({ queryKey: ['inbound_buffer_map_view', warehouseId] }),
        queryClient.invalidateQueries({ queryKey: ['warehouse_locations', warehouseId] }),
        queryClient.invalidateQueries({ queryKey: ['item_stock_by_zone', warehouseId] }),
      ]);
    },
  });
};
