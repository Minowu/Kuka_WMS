import type { DeviceType } from '@/types/auditLog';

/** Sent as X-Client-Type. Backend prefers the IP -> device registry when the IP is registered. */
export function getClientType(pathname: string = window.location.pathname): DeviceType {
  if (pathname.startsWith('/pda')) return 'pda';
  if (pathname.startsWith('/tv')) return 'tv';
  return 'desktop';
}
