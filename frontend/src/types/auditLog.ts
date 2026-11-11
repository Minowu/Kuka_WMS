export type AuditEventType = 'LOGIN' | 'LOGOUT' | 'PERMISSION_DENIED' | 'TOKEN_INVALID';
export type LogResult = 'SUCCESS' | 'FAILED';
export type DeviceType = 'pda' | 'tv' | 'desktop';
export type ActionMethod = 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface AuditLog {
  id: number;
  event_type: AuditEventType;
  result: LogResult;
  failure_reason: string | null;
  user_id: number | null;
  username: string | null;
  ip: string | null;
  user_agent: string | null;
  device_type: DeviceType | null;
  device_name: string | null;
  request_id: string | null;
  path: string | null;
  created_at: string;
}

export interface ActionLog {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string | null;
  method: ActionMethod;
  route_template: string | null;
  path: string;
  resource_type: string | null;
  resource_id: string | null;
  status_code: number;
  result: LogResult;
  error_message: string | null;
  payload: unknown;
  query_params: Record<string, string> | null;
  duration_ms: number | null;
  ip: string | null;
  device_type: DeviceType | null;
  device_name: string | null;
  request_id: string | null;
  created_at: string;
}

export interface LogListResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CommonLogParams {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  username?: string;
  result?: LogResult;
  ip?: string;
  device_name?: string;
}

export interface AuditLogParams extends CommonLogParams {
  event_type?: AuditEventType;
}

export interface ActionLogParams extends CommonLogParams {
  action?: string;
  method?: ActionMethod;
  resource_type?: string;
}

export interface Device {
  id: number;
  ip_address: string;
  name: string;
  device_type: DeviceType;
  description: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}
