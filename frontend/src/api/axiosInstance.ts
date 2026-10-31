import axios, { InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/useAuthStore';
import { refreshAccessTokenApi } from './authRefresh';
import {
  forceLogout,
  hasValidRefreshToken,
  isAuthApiUrl,
  isRefreshApiUrl,
} from '@/utils/authSession';
import { generateUuid } from '@/utils/randomId';
import { logger } from '@/logger';

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _requestStartTime?: number;
  _requestId?: string;
}

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || undefined,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: string | null) => void;
  reject: (reason: unknown) => void;
}> = [];

const processQueue = (error: unknown, access_token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(access_token);
    }
  });
  failedQueue = [];
};

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    const customConfig = config as CustomAxiosRequestConfig;
    const access_token = useAuthStore.getState().access_token;
    if (access_token && customConfig.headers && !isAuthApiUrl(customConfig.url)) {
      customConfig.headers.Authorization = `Bearer ${access_token}`;
    }
    // Let axios/browser set multipart boundary for file uploads
    if (customConfig.data instanceof FormData && customConfig.headers) {
      delete customConfig.headers['Content-Type'];
    }

    // Generate or preserve X-Request-ID (uuid) per request
    const existingRequestId = customConfig.headers?.['X-Request-ID'] as string | undefined;
    const requestId = existingRequestId || generateUuid();
    if (customConfig.headers) {
      customConfig.headers['X-Request-ID'] = requestId;
    }
    customConfig._requestStartTime = performance.now();
    customConfig._requestId = requestId;

    return customConfig;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config as CustomAxiosRequestConfig | undefined;

    // Log 4xx/5xx errors
    const status = error.response?.status;
    const url = originalRequest?.url || '';
    const isLogEndpoint = url.includes('/api/v1/logs/client');

    if (!isLogEndpoint && originalRequest) {
      const startTime = originalRequest._requestStartTime;
      const duration =
        typeof startTime === 'number'
          ? Math.round(performance.now() - startTime)
          : undefined;
      const requestId =
        originalRequest._requestId ||
        (originalRequest.headers?.['X-Request-ID'] as string | undefined);

      if (status && status >= 400) {
        logger.error(
          `HTTP ${originalRequest.method?.toUpperCase() || 'REQUEST'} ${url} [${status}]`,
          {
            method: originalRequest.method?.toUpperCase(),
            url,
            status,
            request_body: originalRequest.data,
            response_body: error.response?.data,
            duration,
            correlation_id: requestId,
          },
        );
      }
    }

    if (error.response?.status === 401 && originalRequest) {
      if (isAuthApiUrl(originalRequest.url)) {
        if (isRefreshApiUrl(originalRequest.url)) {
          processQueue(error, null);
          isRefreshing = false;
          forceLogout();
        }
        return Promise.reject(error);
      }

      if (originalRequest._retry) {
        forceLogout();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise<string | null>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((access_token) => {
            if (originalRequest.headers && access_token) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }
            return axiosInstance(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refresh_token = useAuthStore.getState().refresh_token;
      if (!hasValidRefreshToken(refresh_token)) {
        processQueue(error, null);
        isRefreshing = false;
        forceLogout();
        return Promise.reject(error);
      }

      try {
        const data = await refreshAccessTokenApi(refresh_token!);
        const { access_token, refresh_token: newRefreshToken } = data;

        useAuthStore.getState().setToken(access_token, newRefreshToken);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        processQueue(null, access_token);
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        forceLogout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  },
);

export default axiosInstance;
