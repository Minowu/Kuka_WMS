import { logger } from './clientLogger';

let isInitialized = false;

export function initGlobalErrorLogging(): void {
  if (isInitialized || typeof window === 'undefined') return;
  isInitialized = true;

  // window.onerror hook
  const prevOnError = window.onerror;
  window.onerror = (message, source, lineno, colno, error) => {
    logger.error(typeof message === 'string' ? message : 'Unhandled window error', {
      filename: source,
      lineno,
      colno,
      stack: error?.stack,
      error_name: error?.name,
    });

    if (typeof prevOnError === 'function') {
      return prevOnError(message, source, lineno, colno, error);
    }
    return false;
  };

  // unhandledrejection hook
  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    const reason = event.reason;
    const msg =
      reason instanceof Error
        ? reason.message
        : typeof reason === 'string'
        ? reason
        : 'Unhandled Promise Rejection';
    const stack = reason instanceof Error ? reason.stack : undefined;

    logger.error(`Unhandled Promise Rejection: ${msg}`, {
      stack,
      reason:
        reason instanceof Error
          ? { name: reason.name, message: reason.message }
          : reason,
    });
  });
}
