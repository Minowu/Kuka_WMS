import type { AvailableMapNode } from '@/types/station';

export interface SlotFormItem {
  id?: number;
  position_index: number;
  location_code: string;
  node_label?: string;
  map_x?: number;
  map_y?: number;
}

export interface AssignedNodeInfo {
  id?: number;
  name: string;
  zone: string;
}

export interface NodeOptionFilter {
  currentLocationId?: number | null;
  selectedInForm?: (string | undefined)[];
  currentSlotNode?: string;
}

export interface NodeOption {
  value: string;
  disabled: boolean;
  label: string;
  node: AvailableMapNode;
}

export interface MapPickerOptions {
  title: string;
  isOverview?: boolean;
  currentSelectedNodeLabel?: string;
  currentLocationId?: number | null;
  selectedInForm?: (string | undefined)[];
  onSelect: (node: AvailableMapNode) => void;
}

/** Bộ công cụ chọn Node bản đồ, truyền xuống các tab để không phải truyền lẻ từng prop. */
export interface NodeTools {
  availableNodes: AvailableMapNode[];
  getNodeOptions: (filter?: NodeOptionFilter) => NodeOption[];
  matchNodeLabel: (val?: string | null, locCode?: string | null) => string | undefined;
  openMapPicker: (options: MapPickerOptions) => void;
}

export interface BannerTheme {
  bannerClass: string;
  iconClass: string;
  textClass: string;
  buttonClass: string;
}
