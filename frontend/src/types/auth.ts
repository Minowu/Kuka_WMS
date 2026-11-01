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

export type UserModule = 'operator_raw' | 'operator_cnc' | 'operator_washing';

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
  location_ids?: number[];
}

export interface UpdateUserInput {
  email?: string;
  password?: string;
  password_confirm?: string;
  role_ids?: number[];
  is_admin?: boolean;
  location_ids?: number[];
}

