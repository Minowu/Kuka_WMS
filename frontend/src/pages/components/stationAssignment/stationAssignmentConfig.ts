import type { User } from '@/types/auth';
import type { StationCatalogResponse } from '@/types/station';

export type ProductionArea = 'raw_material' | 'cnc' | 'washing';

export const AREA_NAMES: Record<ProductionArea, string> = {
  raw_material: 'Khu Cấp Phôi',
  cnc: 'Khu Máy CNC',
  washing: 'Khu Tẩy Rửa',
};

export interface LocationGridTheme {
  title: string;
  selectAllClass: string;
  selectedItemClass: string;
  gridClass: string;
}

export const LOCATION_GRID_THEMES: Record<'raw_material' | 'washing', LocationGridTheme> = {
  raw_material: {
    title: 'Danh sách Ô Cấp Phôi (Nguyên Liệu)',
    selectAllClass: 'text-amber-700 hover:text-amber-800',
    selectedItemClass: 'border-amber-500 bg-amber-50/80 font-semibold text-amber-950 shadow-2xs',
    gridClass: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4',
  },
  washing: {
    title: 'Danh sách Slot Khu Tẩy Rửa',
    selectAllClass: 'text-emerald-700 hover:text-emerald-800',
    selectedItemClass: 'border-emerald-500 bg-emerald-50/80 font-semibold text-emerald-950 shadow-2xs',
    gridClass: 'grid-cols-2 sm:grid-cols-4',
  },
};

export function getAreaLocationIds(catalog: StationCatalogResponse, area: ProductionArea): number[] {
  if (area === 'raw_material') return (catalog.raw_materials || []).map((r) => r.id);
  if (area === 'washing') return (catalog.washing_slots || []).map((w) => w.id);
  return (catalog.machines || []).flatMap((m) => (m.slots || []).map((s) => s.id));
}

/** Khu vực mà role của tài khoản bị giới hạn. Trả về null nếu role không gắn với khu nào. */
export function getRoleArea(user: User | null): ProductionArea | null {
  const roleNames = (user?.roles || []).map((r) => r.name.toLowerCase());
  if (roleNames.some((r) => r.includes('raw'))) return 'raw_material';
  if (roleNames.some((r) => r.includes('wash'))) return 'washing';
  if (roleNames.some((r) => r.includes('cnc'))) return 'cnc';
  return null;
}

/** Ưu tiên khu theo role; nếu không có thì đoán theo các vị trí đã được gán trước đó. */
export function detectUserArea(
  user: User,
  catalog: StationCatalogResponse,
  userLocationIds: number[]
): ProductionArea {
  const roleArea = getRoleArea(user);
  if (roleArea) return roleArea;

  const hasLocationIn = (area: ProductionArea) => {
    const areaIds = new Set(getAreaLocationIds(catalog, area));
    return userLocationIds.some((id) => areaIds.has(id));
  };
  const hasRaw = hasLocationIn('raw_material');
  const hasWash = hasLocationIn('washing');
  const hasCnc = hasLocationIn('cnc');

  if (hasRaw && !hasCnc && !hasWash) return 'raw_material';
  if (hasWash && !hasCnc && !hasRaw) return 'washing';
  return 'cnc';
}
