import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { listActionLogsApi, listAuditLogsApi, listDevicesApi } from '@/api/auditLog';
import type { ActionLogParams, AuditLogParams } from '@/types/auditLog';

export const useAuditLogs = (params: AuditLogParams) => {
  return useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => listAuditLogsApi(params),
    placeholderData: keepPreviousData,
  });
};

export const useActionLogs = (params: ActionLogParams) => {
  return useQuery({
    queryKey: ['action-logs', params],
    queryFn: () => listActionLogsApi(params),
    placeholderData: keepPreviousData,
  });
};

export const useDevices = () => {
  return useQuery({
    queryKey: ['devices'],
    queryFn: listDevicesApi,
    staleTime: 5 * 60 * 1000,
  });
};
