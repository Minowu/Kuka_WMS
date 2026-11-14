import { message } from '@/components/ui';
import { getApiErrorMessage } from '@/utils/apiErrorMessage';

/** Lỗi validate form (errorFields) đã hiển thị dưới ô nhập nên bỏ qua, chỉ báo lỗi từ API. */
export function showStationError(err: unknown, fallback: string) {
  if ((err as { errorFields?: unknown })?.errorFields) return;
  message.error(getApiErrorMessage(err, fallback));
}
