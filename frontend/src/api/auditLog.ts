import axiosInstance from './axiosInstance';
import type {
  ActionLog,
  ActionLogParams,
  AuditLog,
  AuditLogParams,
  Device,
  LogListResponse,
} from '@/types/auditLog';

export const listAuditLogsApi = async (
  params: AuditLogParams,
): Promise<LogListResponse<AuditLog>> => {
  const { data } = await axiosInstance.get<LogListResponse<AuditLog>>('/api/v1/audit-logs', {
    params,
  });
  return data;
};

export const listActionLogsApi = async (
  params: ActionLogParams,
): Promise<LogListResponse<ActionLog>> => {
  const { data } = await axiosInstance.get<LogListResponse<ActionLog>>('/api/v1/action-logs', {
    params,
  });
  return data;
};

export const listDevicesApi = async (): Promise<Device[]> => {
  const { data } = await axiosInstance.get<Device[]>('/api/v1/devices');
  return data;
};
