export interface WarehouseLocation {
  id: number;
  location_code: string;
  node_name: string | null;
  zone_id: number | null;
  row: string | null;
  column: string | null;
  level: string | null;
  bin: string | null;
  capacity: number | null;
  location_type?: string;
  machine_code?: string | null;
  position_index?: number | null;
  default_stage_level?: number | null;
  status?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ItemStockRow {
  id: number;
  product_id: number;
  location_id: number;
  lot_number: string | null;
  expiry_date: string | null;
  quantity: string;
  reserved_quantity: string;
  available_quantity: string;
  status: string;
  created_at: string | null;
  updated_at: string;
}

export interface EmptyLocation {
  id: number;
  location_code: string;
  level: string | null;
  row: string | null;
  column: string | null;
  bin: string | null;
  location_type?: string | null;
}

export interface SuggestEmptyLocationsInput {
  zone_id: number;
  count: number;
  exclude_location_ids?: number[];
}

export interface SuggestEmptyLocationsResponse {
  suggestions: EmptyLocation[];
  total_available: number;
}

export interface EmptyLocationsListResponse {
  locations: EmptyLocation[];
  total_available: number;
}

export type StorageStockStatus = 'empty' | 'occupied';

export interface StorageLocation {
  id: number;
  location_code: string;
  status: string;
  has_stock: boolean;
  level: string | null;
  row: string | null;
  column: string | null;
  bin: string | null;
  product_sku: string | null;
  product_name: string | null;
  quantity: number;
}

export interface StorageLocationsListResponse {
  zone_id: number;
  stock_status: StorageStockStatus;
  locations: StorageLocation[];
  total_available: number;
}

export interface StorageRelocateInput {
  zone_id: number;
  source_location_id: number;
  destination_location_id: number;
}

export interface StorageRelocateStockMoved {
  item_stock_id: number;
  product_id: number;
  quantity: number;
  reserved_quantity: number;
}

export interface StorageRelocateResult {
  zone_id: number;
  command_id?: number | null;
  source_location_id: number;
  source_location_code: string;
  source_status: string;
  destination_location_id: number;
  destination_location_code: string;
  destination_status: string;
  moved_stocks: StorageRelocateStockMoved[];
  moved_pallet_quantity: number;
}

export interface StorageRelocateCommand {
  id: number;
  zone_id: number;
  source_location_id: number | null;
  destination_location_id: number | null;
  source_location_code: string;
  destination_location_code: string;
  status: string;
  command_data: {
    moved_stocks?: StorageRelocateStockMoved[];
    moved_pallet_quantity?: number;
    moved_stock_count?: number;
    total_quantity?: number;
    [key: string]: unknown;
  };
  created_by_id: number | null;
  created_by_name: string | null;
  created_at: string;
}

export interface StorageRelocateCommandListResponse {
  zone_id: number;
  commands: StorageRelocateCommand[];
  total: number;
}

export interface LocationStockLabel {
  location_id: number;
  location_code: string;
  is_empty: boolean;
  display_status: string;
  product_sku: string | null;
  product_name: string | null;
  /** Mã bin của location (warehouse_locations.bin) — đã chuẩn hóa theo type. */
  bin: string | null;
  location_type?: string | null;
  quantity: number;
  line_count: number;
  inbound_order_detail_id?: number | null;
  inbound_order_id?: number | null;
  lot?: string | null;
  lot_number?: string | null;
}

export interface LocationStockLabelsResponse {
  zone_id: number;
  cells: LocationStockLabel[];
}
