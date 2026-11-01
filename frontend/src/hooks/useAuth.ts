import { useAppStore } from '@/store/useAppStore';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  loginApi,
  getUsersApi,
  deleteUserApi,
  createUserApi,
  updateUserApi,
  getRolesApi,
} from '@/api/auth';
import { useAuthStore } from '@/store/useAuthStore';
import { getHomePathFromUser } from '@/utils/authSession';
import type {
  CreateUserInput,
  LoginRequest,
  LoginResponse,
  RoleBrief,
  UpdateUserInput,
  User,
  UserListResponse,
} from '@/types/auth';
import { AxiosError } from 'axios';
import { ApiErrorResponse } from '@/types/apiError';

export const useLogin = () => {
  const setAuth = useAuthStore((state) => state.setAuth);
  const navigate = useNavigate();

  return useMutation<LoginResponse, Error, LoginRequest>({
    mutationFn: loginApi,
    onSuccess: (data, variables) => {
      setAuth(
        data.access_token,
        data.refresh_token,
        data.user,
        undefined, // zone_id
      );
      navigate(getHomePathFromUser(data.user));
    },
  });
};

export const useLogout = () => {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  return () => {
    clearAuth();
    queryClient.clear();
    queryClient.removeQueries({ queryKey: ['warehouse'] });
    navigate('/login', { replace: true });
  };
};

export const useUser = () => {
  return useQuery<User[], Error>({
    queryKey: ['user'],
    queryFn: async () => {
      const data: UserListResponse = await getUsersApi({ page_size: 100 });
      return data.items;
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useRoles = () => {
  return useQuery<RoleBrief[], Error>({
    queryKey: ['roles'],
    queryFn: getRolesApi,
    staleTime: 10 * 60 * 1000,
  });
};

export const useCreateUser = () => {
  const queryClient = useQueryClient();
  return useMutation<User, AxiosError<ApiErrorResponse>, CreateUserInput>({
    mutationFn: createUserApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
};

export const useUpdateUser = () => {
  const queryClient = useQueryClient();
  return useMutation<
    User,
    AxiosError<ApiErrorResponse>,
    { id: number; data: UpdateUserInput }
  >({
    mutationFn: ({ id, data }) => updateUserApi(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
};

export const useDeleteUser = () => {
  const queryClient = useQueryClient();
  return useMutation<void, AxiosError<ApiErrorResponse>, number>({
    mutationFn: deleteUserApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });
};
