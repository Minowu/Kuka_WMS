import axiosInstance from './axiosInstance';
import type {
  CreateUserInput,
  LoginApiResponse,
  LoginRequest,
  LoginResponse,
  RoleBrief,
  UpdateUserInput,
  User,
  UserListResponse,
} from '@/types/auth';

export const loginApi = async (data: LoginRequest): Promise<LoginResponse> => {
  const response = await axiosInstance.post<LoginApiResponse>(
    '/api/v1/auth/login',
    data,
  );
  const { user, tokens } = response.data;
  
  return {
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token ?? null,
    token_type: tokens.token_type ?? 'bearer',
    user,
  };
};

export { refreshAccessTokenApi as refreshApi } from './authRefresh';

export const getUsersApi = async (params?: {
  page?: number;
  page_size?: number;
}): Promise<UserListResponse> => {
  const response = await axiosInstance.get<UserListResponse>('/api/v1/users', {
    params: {
      page: params?.page ?? 1,
      page_size: params?.page_size ?? 100,
    },
  });
  return response.data;
};

/** Active non-admin usernames for tablet assign-by picker */
export const getStaffUsernamesApi = async (): Promise<string[]> => {
  const response = await axiosInstance.get<{ usernames: string[] }>(
    '/api/v1/users/staff-usernames',
  );
  return response.data.usernames;
};

/** Lấy danh sách toàn bộ các Role trong hệ thống */
export const getRolesApi = async (): Promise<RoleBrief[]> => {
  const response = await axiosInstance.get<RoleBrief[]>('/api/v1/auth/roles');
  return response.data;
};

/** @deprecated use getUsersApi — kept for older callers expecting an array */
export const getUserApi = async (): Promise<User[]> => {
  const data = await getUsersApi();
  return data.items;
};

export const updateUserApi = async (
  id: number,
  data: UpdateUserInput,
): Promise<User> => {
  const response = await axiosInstance.patch<User>(`/api/v1/users/${id}`, data);
  return response.data;
};

export const createUserApi = async (data: CreateUserInput): Promise<User> => {
  const response = await axiosInstance.post<{
    id: number;
    username: string;
    email: string;
    roles: User['roles'];
    warehouses?: User['warehouses'];
    access: User['access'];
    is_active: boolean;
  }>('/api/v1/auth/signup', data);
  const body = response.data;
  return {
    id: body.id,
    username: body.username,
    email: body.email,
    roles: body.roles ?? [],
    warehouses: body.warehouses ?? [],
    access: body.access,
    is_active: body.is_active,
    created_at: new Date().toISOString(),
  };
};

export const deleteUserApi = async (id: number): Promise<void> => {
  await axiosInstance.delete(`/api/v1/users/${id}`);
};
