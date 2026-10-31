import { useAuthStore } from '@/store/useAuthStore';
import { generateUuid } from '@/utils/randomId';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

export interface LogEntry {
  ts: string;
  level: LogLevel;
  msg: string;
  context: Record<string, unknown>;
}

export interface ClientLogPayload {
  entries: LogEntry[];
}

const BATCH_SIZE_TRIGGER = 50;
const MAX_BATCH_PER_REQUEST = 100;
const FLUSH_INTERVAL_MS = 5000;

class ClientLogger {
  private buffer: LogEntry[] = [];
  private flushTimer: number | null = null;
  private isFlushing = false;
  private readonly defaultCorrelationId: string = generateUuid();
  private activeCorrelationId: string | null = null;
  private customStationInfo: Record<string, unknown> = {};
  private customDeviceInfo: Record<string, unknown> = {};

  constructor() {
    this.startPeriodicFlush();
    this.registerPageHideHandler();
  }

  private startPeriodicFlush(): void {
    if (typeof window === 'undefined') return;
    this.flushTimer = window.setInterval(() => {
      if (this.buffer.length > 0 && !this.isFlushing) {
        void this.flush();
      }
    }, FLUSH_INTERVAL_MS);
  }

  private registerPageHideHandler(): void {
    if (typeof window === 'undefined') return;

    const flushOnExit = () => {
      this.flushKeepalive();
    };

    window.addEventListener('pagehide', flushOnExit);
    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        flushOnExit();
      }
    });
  }

  public setCorrelationId(id: string | null): void {
    this.activeCorrelationId = id;
  }

  public getCorrelationId(): string {
    return this.activeCorrelationId || this.defaultCorrelationId;
  }

  public setStationInfo(info: Record<string, unknown>): void {
    this.customStationInfo = { ...this.customStationInfo, ...info };
  }

  public setDeviceInfo(info: Record<string, unknown>): void {
    this.customDeviceInfo = { ...this.customDeviceInfo, ...info };
  }

  private buildContext(extraContext?: Record<string, unknown>): Record<string, unknown> {
    const route =
      typeof window !== 'undefined'
        ? `${window.location.pathname}${window.location.search}`
        : '';

    let currentUser: { id: number; username: string; email?: string } | null = null;
    let zoneId: number | null = null;

    try {
      const authState = useAuthStore.getState();
      if (authState?.user) {
        currentUser = {
          id: authState.user.id,
          username: authState.user.username,
          email: authState.user.email,
        };
      }
      if (authState?.zone_id) {
        zoneId = authState.zone_id;
      }
    } catch {
      // Ignore if auth store is unavailable
    }

    const stationCandidate: Record<string, unknown> = { ...this.customStationInfo };
    try {
      const storedZone = zoneId ?? localStorage.getItem('zone_id');
      const storedStation = localStorage.getItem('station_id');
      const storedDevice = localStorage.getItem('device_id');
      if (storedZone) stationCandidate.zone_id = Number(storedZone) || storedZone;
      if (storedStation) stationCandidate.station_id = storedStation;
      if (storedDevice) stationCandidate.device_id = storedDevice;
    } catch {
      // Ignore localStorage errors
    }
    const station = Object.keys(stationCandidate).length > 0 ? stationCandidate : null;

    const deviceInfo: Record<string, unknown> = {
      ...this.customDeviceInfo,
    };
    if (typeof window !== 'undefined' && window.screen) {
      deviceInfo.screen_width = window.screen.width;
      deviceInfo.screen_height = window.screen.height;
    }

    const userAgent = typeof navigator !== 'undefined' ? navigator.userAgent : '';
    const correlation_id =
      (extraContext?.correlation_id as string) || this.getCorrelationId();

    return {
      route,
      user: currentUser,
      station,
      device: Object.keys(deviceInfo).length > 0 ? deviceInfo : null,
      userAgent,
      correlation_id,
      ...(extraContext || {}),
    };
  }

  public log(level: LogLevel, msg: string, context?: Record<string, unknown>): void {
    const entry: LogEntry = {
      ts: new Date().toISOString(),
      level,
      msg,
      context: this.buildContext(context),
    };

    this.buffer.push(entry);

    if (this.buffer.length >= BATCH_SIZE_TRIGGER && !this.isFlushing) {
      void this.flush();
    }
  }

  public debug(msg: string, context?: Record<string, unknown>): void {
    this.log('debug', msg, context);
  }

  public info(msg: string, context?: Record<string, unknown>): void {
    this.log('info', msg, context);
  }

  public warn(msg: string, context?: Record<string, unknown>): void {
    this.log('warn', msg, context);
  }

  public error(msg: string, context?: Record<string, unknown>): void {
    this.log('error', msg, context);
  }

  private getAuthToken(): string | null {
    try {
      const token = useAuthStore.getState().access_token;
      if (token) return token;
    } catch {
      // ignore
    }
    try {
      return localStorage.getItem('access_token');
    } catch {
      return null;
    }
  }

  private getEndpoint(): string {
    const base = import.meta.env.VITE_API_URL;
    if (base && typeof base === 'string' && base.trim().length > 0) {
      return `${base.replace(/\/$/, '')}/api/v1/logs/client`;
    }
    return '/api/v1/logs/client';
  }

  public async flush(): Promise<void> {
    if (this.isFlushing || this.buffer.length === 0) return;
    this.isFlushing = true;

    try {
      while (this.buffer.length > 0) {
        const batch = this.buffer.splice(0, MAX_BATCH_PER_REQUEST);
        await this.sendBatchWithRetry(batch);
      }
    } finally {
      this.isFlushing = false;
    }
  }

  private flushKeepalive(): void {
    if (this.buffer.length === 0) return;

    while (this.buffer.length > 0) {
      const batch = this.buffer.splice(0, MAX_BATCH_PER_REQUEST);
      this.sendKeepalive(batch);
    }
  }

  private sendKeepalive(batch: LogEntry[]): void {
    const url = this.getEndpoint();
    const token = this.getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers.Authorization = `Bearer ${token.replace(/^Bearer\s+/i, '')}`;
    }

    try {
      fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({ entries: batch }),
        keepalive: true,
      }).catch(() => {
        // Drop on failure; never log error of the logging request itself
      });
    } catch {
      // Drop on failure
    }
  }

  private async sendBatchWithRetry(batch: LogEntry[]): Promise<boolean> {
    const url = this.getEndpoint();
    const token = this.getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers.Authorization = `Bearer ${token.replace(/^Bearer\s+/i, '')}`;
    }
    const body = JSON.stringify({ entries: batch });

    // Attempt 1
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body,
      });
      if (res.ok) return true;
    } catch {
      // First attempt failed
    }

    // Wait 1000ms before 1 retry
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Attempt 2 (the 1 retry)
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body,
      });
      if (res.ok) return true;
    } catch {
      // Second attempt failed
    }

    // Drop on failure after 1 retry; never loop or log errors of the logging request itself
    return false;
  }
}

export const logger = new ClientLogger();
