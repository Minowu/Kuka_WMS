import type { ActionMethod, AuditEventType, DeviceType, LogResult } from '@/types/auditLog';

export const AUDIT_EVENT_LABELS: Record<AuditEventType, string> = {
  LOGIN: 'Đăng nhập',
  LOGOUT: 'Đăng xuất',
  PERMISSION_DENIED: 'Bị từ chối quyền',
  TOKEN_INVALID: 'Token không hợp lệ',
};

export const FAILURE_REASON_LABELS: Record<string, string> = {
  USER_NOT_FOUND: 'Tài khoản không tồn tại',
  WRONG_PASSWORD: 'Sai mật khẩu',
  INACTIVE_USER: 'Tài khoản bị khoá',
  INSUFFICIENT_PERMISSION: 'Không đủ quyền',
  INVALID_SIGNATURE: 'Sai chữ ký token',
  INVALID_CLAIMS: 'Token sai thông tin',
  WRONG_TOKEN_TYPE: 'Sai loại token',
  MALFORMED: 'Token sai định dạng',
  MISSING_SUBJECT: 'Token thiếu user',
};

export const LOG_RESULT_LABELS: Record<LogResult, string> = {
  SUCCESS: 'Thành công',
  FAILED: 'Thất bại',
};

export const DEVICE_TYPE_LABELS: Record<DeviceType, string> = {
  pda: 'PDA',
  tv: 'TV',
  desktop: 'Máy tính',
};

export const ACTION_METHODS: ActionMethod[] = ['POST', 'PUT', 'PATCH', 'DELETE'];

export const LOG_PAGE_SIZE = 20;
