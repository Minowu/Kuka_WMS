import { z } from 'zod';

export const loginSchema = z.object({
  username: z.string().min(1, 'Vui lòng nhập tài khoản'),
  password: z.string().min(1, 'Vui lòng nhập mật khẩu'),
});

export type LoginRequest = z.infer<typeof loginSchema>;

export interface RoleBrief {
  id: number;
  name: string;
}

export interface WarehouseBrief {
  id: number;
  code: string;
  name: string | null;
}

export type UserModule = 'inbound' | 'outbound' | 'stocktake';

export type WarehouseScope = 'all' | 'assigned';

/** Aggregated access from backend — not raw permission codes. */
export interface UserAccessSummary {
  is_admin: boolean;
  warehouse_scope: WarehouseScope;
  warehouses: WarehouseBrief[];
  modules: UserModule[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string | null;
  token_type?: string;
}

/** Raw login payload from backend */
export interface LoginApiResponse {
  user: User;
  tokens: AuthTokens;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
  token_type?: string;
  refresh_token?: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  roles: RoleBrief[];
  warehouses: WarehouseBrief[];
  access: UserAccessSummary;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateUserInput {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  role_ids?: number[];
  is_admin?: boolean;
  warehouse_ids?: number[];
  modules?: UserModule[];
}

export interface UpdateUserInput {
  email?: string;
  password?: string;
  password_confirm?: string;
  role_ids?: number[];
  is_admin?: boolean;
  warehouse_ids?: number[];
  modules?: UserModule[];
}

/** Temporary role options until BE exposes GET /roles */
export const ROLE_OPTIONS: RoleBrief[] = [
  { id: 2, name: 'admin' },
  { id: 3, name: 'operator_raw' },
  { id: 4, name: 'operator_cnc' },
  { id: 5, name: 'operator_washing' },
  { id: 1, name: 'operator' },
];

export const MODULE_OPTIONS: { key: UserModule; label: string }[] = [
  { key: 'inbound', label: 'Đơn nhập' },
  { key: 'outbound', label: 'Đơn xuất' },
  { key: 'stocktake', label: 'Kiểm kê' },
];

export const MODULE_ROLE_NAMES: UserModule[] = [
  'inbound',
  'outbound',
  'stocktake',
];
