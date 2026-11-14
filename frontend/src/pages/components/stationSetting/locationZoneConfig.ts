import type { StationLocationCreateInput } from '@/types/station';
import type { BannerTheme } from './stationSettingTypes';

export type LocationZoneKey = 'raw_material' | 'washing' | 'empty_buffer';

export interface LocationZoneConfig {
  locationType: StationLocationCreateInput['location_type'];
  /** Tiền tố tên mặc định khi thêm mới, ví dụ VT → VT-01 */
  namePrefix: string;
  /** Tên thường dùng trong câu thông báo, ví dụ "ô cấp phôi" */
  entityLabel: string;
  /** Tên viết hoa dùng trong tiêu đề, ví dụ "Ô Cấp Phôi" */
  entityTitle: string;
  infoTitle: string;
  infoText: string;
  addButtonText: string;
  createModalTitle: string;
  createOkText: string;
  namePlaceholder: string;
  /** name_first: cột tên đứng đầu; code_first: cột mã đứng đầu */
  tableLayout: 'name_first' | 'code_first';
  nameColumnTitle?: string;
  codeColumnTitle?: string;
  theme: BannerTheme & { badgeClass: string; editHoverClass: string };
}

export const LOCATION_ZONES: Record<LocationZoneKey, LocationZoneConfig> = {
  raw_material: {
    locationType: 'RAW_MATERIAL',
    namePrefix: 'VT',
    entityLabel: 'ô cấp phôi',
    entityTitle: 'Ô Cấp Phôi',
    infoTitle: 'Khu Cấp Phôi (Nguyên Liệu):',
    infoText:
      'Các ô tiếp nhận xe Rack gá phôi thô từ kho. AMR sẽ tự động di chuyển đến các vị trí này để nhận phôi khi máy CNC kích hoạt lệnh gọi.',
    addButtonText: 'Thêm Ô Cấp Phôi',
    createModalTitle: 'Thêm Ô Cấp Phôi (Nguyên Liệu)',
    createOkText: 'Thêm ô',
    namePlaceholder: 'Ví dụ: VT-01, Ô Cấp Phôi 1...',
    tableLayout: 'name_first',
    theme: {
      bannerClass: 'bg-amber-50/60 border-amber-200/80',
      iconClass: 'text-amber-600',
      textClass: 'text-amber-900',
      buttonClass: '!bg-amber-600 hover:!bg-amber-700',
      badgeClass: 'text-amber-900 bg-amber-50 border-amber-200',
      editHoverClass: 'hover:text-brand-primary',
    },
  },
  washing: {
    locationType: 'WASHING_SLOT',
    namePrefix: 'WASH',
    entityLabel: 'slot tẩy rửa',
    entityTitle: 'Slot Tẩy Rửa',
    infoTitle: 'Khu Tẩy Rửa:',
    infoText:
      'Trạm tẩy rửa tiếp nhận xe phôi sau khi hoàn thành công đoạn CNC cuối cùng. Xe sau khi làm sạch sẽ được dỡ phôi và đưa sang bãi đệm xe rỗng.',
    addButtonText: 'Thêm Slot Tẩy Rửa',
    createModalTitle: 'Thêm Slot Khu Tẩy Rửa',
    createOkText: 'Thêm slot',
    namePlaceholder: 'Ví dụ: WASH-01, Bồn Rửa 1...',
    tableLayout: 'code_first',
    nameColumnTitle: 'Tên Slot',
    codeColumnTitle: 'Mã Slot',
    theme: {
      bannerClass: 'bg-emerald-50/60 border-emerald-200/80',
      iconClass: 'text-emerald-600',
      textClass: 'text-emerald-900',
      buttonClass: '!bg-emerald-600 hover:!bg-emerald-700',
      badgeClass: 'text-emerald-900 bg-emerald-50 border-emerald-200',
      editHoverClass: 'hover:text-emerald-600',
    },
  },
  empty_buffer: {
    locationType: 'EMPTY_CART_BUFFER',
    namePrefix: 'EMPTY',
    entityLabel: 'bãi đệm',
    entityTitle: 'Bãi Đệm',
    infoTitle: 'Bãi Đệm Xe Rỗng (Empty Cart Buffer):',
    infoText:
      'Vị trí tập kết các xe Rack rỗng (đã dỡ sạch chi tiết). Khi khu Cấp Phôi hoặc các trạm phát sinh nhu cầu, AMR sẽ đến bãi đệm này lấy xe rỗng đi phục vụ.',
    addButtonText: 'Thêm Bãi Đệm',
    createModalTitle: 'Thêm Bãi Đệm Xe Rỗng',
    createOkText: 'Thêm bãi đệm',
    namePlaceholder: 'Ví dụ: EMPTY-01, Bãi Đệm 1...',
    tableLayout: 'code_first',
    nameColumnTitle: 'Tên Bãi Đệm',
    codeColumnTitle: 'Mã Bãi Đệm',
    theme: {
      bannerClass: 'bg-blue-50/60 border-blue-200/80',
      iconClass: 'text-blue-600',
      textClass: 'text-blue-900',
      buttonClass: '!bg-blue-600 hover:!bg-blue-700',
      badgeClass: 'text-blue-900 bg-blue-50 border-blue-200',
      editHoverClass: 'hover:text-blue-600',
    },
  },
};
