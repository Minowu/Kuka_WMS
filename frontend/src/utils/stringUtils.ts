import type { InboundOrderAllocationCreate } from "@/types/inboundOrder";
import { normalizeLotNumber } from "@/utils/lotNumberValidation";

const STAFF_LIST_SEPARATOR = ",";

function parseStaffTokens(raw: string | null | undefined): string[] {
  if (!raw?.trim()) {
    return [];
  }
  return raw
    .split(STAFF_LIST_SEPARATOR)
    .map((part) => part.trim())
    .filter(Boolean);
}

/** Gom tên unique, phân tách bằng dấu phẩy (SX, QC, cavity). */
export function normalizeUniqueCommaField(
  raw: string | null | undefined,
): string | undefined {
  const seen = new Set<string>();
  const ordered: string[] = [];

  for (const token of parseStaffTokens(raw)) {
    if (seen.has(token)) {
      continue;
    }
    seen.add(token);
    ordered.push(token);
  }

  return ordered.length > 0 ? ordered.join(STAFF_LIST_SEPARATOR) : undefined;
}

/** Người đóng gói — chỉ giữ một người. */
export function normalizePackingUserField(
  raw: string | null | undefined,
): string | undefined {
  return parseStaffTokens(raw)[0];
}

export interface InboundItemDraftLike {
  item_id?: number;
  quantity: number;
  unit_id?: number;
  lot_number?: string;
  expiry_date?: string | null;
  qr_code_id?: number | null;
  manufacturing_user?: string | null;
  manufacturing_machine?: string | null;
  qc_user?: string | null;
  packing_user?: string | null;
  cavity_number?: string | null;
}

export function hasTabletScanMetadata(item: InboundItemDraftLike): boolean {
  return Boolean(
    item.qr_code_id &&
      (item.manufacturing_user ||
        item.manufacturing_machine ||
        item.qc_user ||
        item.packing_user ||
        item.cavity_number),
  );
}

export function buildInboundAllocationPayload(
  item: InboundItemDraftLike,
  includeTabletMetadata: boolean,
): InboundOrderAllocationCreate {
  const payload: InboundOrderAllocationCreate = {
    item_id: item.item_id!,
    quantity: item.quantity,
    unit_id: item.unit_id!,
    lot_number: normalizeLotNumber(item.lot_number),
    expiry_date: item.expiry_date || null,
    qr_code_id: item.qr_code_id ?? null,
  };

  if (includeTabletMetadata) {
    payload.cavity_number = item.cavity_number ?? null;
    payload.manufacturing_user = item.manufacturing_user ?? null;
    payload.manufacturing_machine = item.manufacturing_machine ?? null;
    payload.qc_user = item.qc_user ?? null;
    payload.packing_user = item.packing_user ?? null;
  }

  return payload;
}
