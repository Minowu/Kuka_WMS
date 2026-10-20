export interface Item {
  id: number
  sku: string
  name: string
  description: string | null
  base_unit: string
  standard_quantity_per_cart?: number
  warehouse_id: number
  supplier: string
  details: Record<string, unknown>
  is_active: boolean
  quantity: number
  total_price: number
  created_at: string
  updated_at: string
}

export interface ItemListParams {
  warehouse_id?: number
  q?: string
  page?: number
  page_size?: number
  /** @deprecated map to page_size */
  limit?: number
  /** @deprecated use warehouse_id */
  offset?: number
  is_active?: boolean
}

export interface ItemListResponse {
  items: Item[]
  total: number
  page?: number
  page_size?: number
}

export type CreateItemInput = {
  sku: string
  name: string
  description?: string | null
  base_unit: number
  standard_quantity_per_cart?: number
  warehouse_id: number
  supplier?: string
  details?: Record<string, unknown>
}

export type UpdateItemInput = Partial<
  Omit<CreateItemInput, 'sku' | 'warehouse_id'> & {
    warehouse_id?: number
    is_active: boolean
  }
>

export interface ItemStock {
  id: number
  item_id: number
  location_id: number
  location_code?: string | null
  location_name?: string | null
  lot_number: string | null
  expiry_date: string | null
  quantity: number
  status: string
  created_at?: string | null
  updated_at?: string
}

export interface ItemDetails {
  item: Item
  stocks: ItemStock[]
  /** Tồn available (không gồm hàng lẻ/split) — dùng preview form outbound */
  available_quantity?: number
  /** Tồn lẻ/split — dùng preview form outbound */
  split_quantity?: number
}

export interface ItemAnalyzeResponse {
  total_items: number
  total_quantity: number
  total_inventory_value: number
  total_low_stock: number
}

export interface ItemImportJobAccepted {
  job_id: string
  status: string
  message: string
}

export interface ItemImportErrorItem {
  row: number
  sku: string
  message: string
}

export interface ItemImportJobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | string
  warehouse_id?: number | null
  zone_id?: number | null
  filename?: string | null
  processed: number
  total: number
  created: number
  updated?: number
  error_count: number
  errors: ItemImportErrorItem[]
  message: string
}

export type QRCodeStatus = 'expired' | 'stocked' | 'available'
export type QrPrintType = 'item' | 'transit' | 'pack'

export interface QRCodeRecent {
  id: number
  code: string
  item_id: number
  item_sku?: string | null
  item_name?: string | null
  item_stock_id: number | null
  qr_type?: QrPrintType | string | null
  created_at: string | null
  status: QRCodeStatus
}

export interface QRCodeRecentListResponse {
  items: QRCodeRecent[]
  total: number
  page: number
  page_size: number
}

export interface GenerateQrCodesResponse {
  html: string
  quantity: number
  page_count: number
  qr_ids: string[]
  display_codes: string[]
  qr_type?: QrPrintType
}

export interface CreateQrCodesResponse {
  codes: string[]
  display_codes: string[]
  qr_type?: QrPrintType
}
