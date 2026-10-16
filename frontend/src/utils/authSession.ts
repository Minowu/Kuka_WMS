import { type UserAccessSummary, type User } from '@/types/auth';
import { useAuthStore } from '@/store/useAuthStore';

const AUTH_API_PATHS = ['/api/v1/auth/login', '/api/v1/auth/refresh', '/api/v1/auth/signup'];

export function isAuthApiUrl(url?: string): boolean {
  if (!url) return false;
  return AUTH_API_PATHS.some((path) => url === path || url.endsWith(path));
}

export function isRefreshApiUrl(url?: string): boolean {
  if (!url) return false;
  return url === '/api/v1/auth/refresh' || url.endsWith('/api/v1/auth/refresh');
}

export function getHomePathFromUser(user: User | null): string {
  if (!user) return '/login';
  if (user.access?.is_admin) return '/dashboard';

  // Định tuyến thẳng vào đúng phân xưởng được phân quyền
  const roleNames = (user.roles || []).map((r) => (r.name || '').toLowerCase());
  const uname = (user.username || '').toLowerCase();

  if (
    roleNames.includes('raw_material') ||
    roleNames.includes('nguyenlieu') ||
    uname.includes('raw') ||
    uname.includes('nguyenlieu')
  ) {
    return '/pda/raw-material';
  }

  if (
    roleNames.includes('washing') ||
    roleNames.includes('tayrua') ||
    uname.includes('wash') ||
    uname.includes('tayrua')
  ) {
    return '/pda/washing';
  }

  // Mặc định tài khoản đứng máy gia công CNC
  return '/pda/cnc';
}

export function hasModuleAccess(
  access: UserAccessSummary | null | undefined,
  module: UserAccessSummary['modules'][number],
): boolean {
  if (!access) return false;
  if (access.is_admin) return true;
  return access.modules.includes(module);
}

/** Admin (or legacy admin role) may pick any warehouse from the list API. */
export function usesAllWarehouseScope(
  access: UserAccessSummary | null | undefined,
): boolean {
  if (access) {
    return access.is_admin || access.warehouse_scope === 'all';
  }
  return false;
}

export function decodeJwtExp(token: string): number | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))) as {
      exp?: number;
    };
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

export function isAccessTokenExpired(token: string | null, skewSeconds = 30): boolean {
  if (!token) return true;
  const exp = decodeJwtExp(token);
  if (exp === null) return false;
  return Date.now() >= (exp - skewSeconds) * 1000;
}

export function forceLogout(): void {
  useAuthStore.getState().clearAuth();
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

export function hasValidRefreshToken(refreshToken: string | null | undefined): boolean {
  return !!refreshToken && refreshToken.trim().length > 0;
}


