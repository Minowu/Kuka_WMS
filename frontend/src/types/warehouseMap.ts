export interface MapData {
  width: number;
  height: number;
  nodeKeys: string[];
  lineKeys: string[];
  nodeArr: (number | string | number[])[][];
  lineArr: (string | number | (number | null)[])[][];
  type?: string;
  xAttrMin?: number;
  yAttrMin?: number;
  floorList?: Record<string, any>[];
  nodeList?: Record<string, any>[];
  edgeList?: Record<string, any>[];
  mapFormat?: string;
}

export interface ZoneMapLayoutNode {
  id: number;
  location_code: string;
  bin_code?: string | null;
  location_name?: string | null;
  row: string | null;
  column: string | null;
  level: string | null;
  map_x: number;
  map_y: number;
}

export interface ZoneMapLayoutResponse {
  zone_id: number;
  warehouse_id: number;
  nodes: ZoneMapLayoutNode[];
}

/** Chuyển mọi tham chiếu của bin bị loại khỏi map sang bin có trong map mới. */
export interface MapRemapEntry {
  from_bin: string;
  to_bin: string;
}

export interface MapSyncMatchedItem {
  location_id: number;
  bin_code?: string | null;
  location_name?: string | null;
  matched_by: string;
  previous_location_code: string;
  location_code: string;
}

export interface MapSyncCreatedItem {
  location_id: number;
  bin_code?: string | null;
  location_name?: string | null;
  location_code: string;
}

export interface MapSyncRemappedItem {
  from_location_id: number;
  from_bin: string;
  to_location_id: number;
  to_bin: string;
  moved: Record<string, number>;
}

export interface MapSyncRetiredItem {
  location_id: number;
  bin_code?: string | null;
  location_name?: string | null;
  references: Record<string, number>;
  quantity?: string | null;
}

export interface MapSyncFreedCode {
  location_id: number;
  bin_code?: string | null;
  location_name?: string | null;
  released_location_code: string;
}

export interface MapSyncUnnamedNode {
  location_code: string;
  node_name?: string | null;
}

export interface MapSyncCounts {
  matched: number;
  created: number;
  remapped: number;
  retired: number;
  blocked: number;
}

export interface WarehouseMapImportResult {
  total_shelves: number;
  matched: MapSyncMatchedItem[];
  created: MapSyncCreatedItem[];
  remapped: MapSyncRemappedItem[];
  retired: MapSyncRetiredItem[];
  blocked: MapSyncRetiredItem[];
  freed_codes: MapSyncFreedCode[];
  nodes_without_bin_code: MapSyncUnnamedNode[];
  counts: MapSyncCounts;
  warehouse_map_id?: number | null;
  source?: string | null;
  moved_cache_entries?: number | null;
  // Backward compatibility fields if needed
  id?: number;
  zone_id?: number;
  message?: string;
}


export interface WarehouseMapMetadata {
  id: number;
  zone_id: number | null;
  source_sha256: string;
  original_filename: string | null;
  zip_sha256: string | null;
  zip_size_bytes: number | null;
  map_type: string | null;
  width: number;
  height: number;
  x_attr_min: number | null;
  y_attr_min: number | null;
  node_count: number;
  shelf_count: number;
  waypoint_count: number;
  line_count: number;
  is_active: boolean;
  created_at: string;
  activated_at: string;
}

export interface InboundBufferPoint {
  id: number;
  location_code: string;
  node_name: string | null;
  status: string;
  row: string | null;
  column: string | null;
  bin: string | null;
  location_type?: string | null;
}

export interface InboundBufferPointsResponse {
  zone_id: number;
  location_type?: string;
  points: InboundBufferPoint[];
}

export interface InboundBufferMapView {
  zone_id: number;
  location_type?: string;
  map: MapData;
  points: InboundBufferPoint[];
  origin: { min_x: number; min_y: number };
  buffer_node_count: number;
  focus_node_count?: number;
}

/** Parsed map node used by WarehouseMapCanvas click/selection. */
export interface NodeInfo {
  x: number;
  y: number;
  type: number;
  content: string;
  name: string;
  isTurn: number;
  shelfIsTurn: number;
  extraTypes: number[];
}


export interface MapLocationItemStock {
  sku: string;
  lot_number: string | null;
  quantity: string;
}

export interface FullLocationDetail {
  id: number;
  location_code: string;
  location_name?: string | null;
  location_label?: string | null;
  location_type?: string | null;
  container_code?: string | null;
  bin_code?: string | null;
  row: string | null;
  column: string | null;
  level: string | null;
  map_x: number | null;
  map_y: number | null;
  status: string;
  item_stock: MapLocationItemStock[];
}

export interface FullLocationsResponse {
  warehouse_id: number;
  location_codes: string[];
  locations: FullLocationDetail[];
}

export interface WarehouseLocationCell {
  id: number;
  location_code: string;
  bin_code?: string | null;
  location_name?: string | null;
  node_name: string | null;
  warehouse_id: number;
  zone_id: number | null;
  row: string | null;
  column: string | null;
  level: string | null;
  status?: string | null;
  location_type?: string;
  bin?: string | null;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ItemStockDetail {
  id: number;
  item_id: number;
  sku: string;
  location_id?: number;
  lot_number: string | null;
  expiry_date: string | null;
  quantity: string;
  status: string;
}

export interface WarehouseLocationItemStockDetail {
  location: WarehouseLocationCell;
  item_stock: ItemStockDetail[];
  summary: {
    item_stock_count: number;
    total_quantity: string;
  };
}
