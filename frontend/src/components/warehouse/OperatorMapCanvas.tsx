/**
 * OperatorMapCanvas — Bản đồ kho vận hành theo 1 hoặc nhiều zone.
 *
 * Tính năng:
 * - Hiển thị ảnh nền mặt sàn (Floor Plan) chuẩn tỉ lệ vật lý 1:1 (1 px = 50 mm = 0.05m AMR Grid).
 * - Tọa độ ô kệ khớp chính xác với bản vẽ (x = map_x * 0.02, y = bgHeight - map_y * 0.02).
 * - Hỗ trợ Zoom mượt mà bằng con lăn chuột (Wheel) tập trung tại vị trí trỏ chuột.
 * - Hỗ trợ Pan mượt mà bằng kéo rê chuột trái (Left Drag), có chống kích hoạt nhầm click khi đang kéo.
 * - Nút chọn / đổi ảnh nền trực tiếp ở góc trên bên phải (Client-only qua ObjectURL).
 * - Click / double-click chọn ô kệ với hệ tọa độ nghịch đảo chính xác.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useZonesMapLayout, useZonesMapStatus } from "@/hooks/useWarehouseMap";
import type { LocationStockLabel } from "@/types/warehouseLocation";
import { type MapContentBounds } from "@/utils/warehouseMapRender";
import { OPERATOR_MAP_CANVAS_DEFAULTS } from "@/constants/operatorDesktopSizes";
import {
  drawShelfStockLabel,
  drawStationOverlayLabel,
} from "@/utils/warehouseMapShelfDraw";
import { formatDisplayBin } from "@/utils/locationBin";
import {
  SHELF_FULL_COLOR,
  SHELF_EMPTY_COLOR,
  SHELF_SELECTED_COLOR,
  SHELF_STROKE_COLOR,
  SHELF_RESERVED_COLOR,
  SHELF_IN_TRANSIT_COLOR,
} from "@/utils/warehouseMapUtils";
import type { ZoneMapLayoutNode } from "@/types/warehouseMap";

const DEFAULT_BG_URL = "/maps/ALK_CNC_floor_1_08_11.png";
const SCALE_MM_TO_PX = 0.02; // 1 px = 50 mm (0.05m)
const LABEL_MIN_SCREEN_PX = 16;
const ZOOM_MIN = 0.05;
const ZOOM_MAX = 5.0;
const ZOOM_FACTOR = 1.15;

// ─── Drawing helpers ──────────────────────────────────────────────────────────
/**
 * Vẽ ô kệ theo trạng thái, cùng thứ tự màu với WarehouseMapCanvas.
 * - reserved   → SHELF_RESERVED_COLOR
 * - in_transit → SHELF_IN_TRANSIT_COLOR
 * - has_stock / có tồn → SHELF_FULL_COLOR
 * - còn lại    → SHELF_EMPTY_COLOR
 */
function drawShelfByStatus(
  ctx: CanvasRenderingContext2D,
  status: string,
  isFull: boolean,
  x: number,
  y: number,
  half: number,
  invScale: number,
) {
  if (status === "reserved") {
    ctx.fillStyle = SHELF_RESERVED_COLOR;
  } else if (status === "in_transit") {
    ctx.fillStyle = SHELF_IN_TRANSIT_COLOR;
  } else if (isFull || status === "has_stock") {
    ctx.fillStyle = SHELF_FULL_COLOR;
  } else {
    ctx.fillStyle = SHELF_EMPTY_COLOR;
  }
  const size = half * 2;
  const radius = Math.max(2, half * 0.15);
  ctx.beginPath();
  ctx.roundRect(x - half, y - half, size, size, radius);
  ctx.fill();
  ctx.strokeStyle = SHELF_STROKE_COLOR;
  ctx.lineWidth = Math.max(0.6, invScale * 0.8);
  ctx.stroke();
}

/**
 * Vẽ viền nổi bật khi ô đang được chọn, dùng màu SHELF_SELECTED_COLOR (xanh lá).
 */
function drawSelectedHighlight(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  half: number,
  invScale: number,
) {
  const size = half * 2;
  const radius = Math.max(2, half * 0.15);
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(x - half, y - half, size, size, radius);
  ctx.fillStyle = `${SHELF_SELECTED_COLOR}55`; // 33% opacity overlay
  ctx.fill();
  ctx.shadowColor = SHELF_SELECTED_COLOR;
  ctx.shadowBlur = Math.max(2, 12 * invScale);
  ctx.strokeStyle = SHELF_SELECTED_COLOR;
  ctx.lineWidth = Math.max(1.2, 2.5 * invScale);
  ctx.stroke();
  ctx.restore();
}

// ─── Types ────────────────────────────────────────────────────────────────────
export type BufferMapCanvasTuning = {
  /** Hệ số zoom sau khi fit (mặc định 0.95). */
  fitScaleFactor?: number;
  /** Padding khi fit, tính theo tỉ lệ cạnh ngắn nhất (mặc định 0.04 = 4%). */
  fitPaddingRatio?: number;
  /** Kích thước world-space cơ sở của ô (mặc định 800 mm). */
  baseNodeSize?: number;
  /**
   * Hệ số kích thước ô: half = baseNodeSize * shelfSizeFactor (mặc định 0.7).
   */
  shelfSizeFactor?: number;
  /** Hệ số phóng chữ label trong ô. */
  labelTextScale?: number;
};

export type BufferCellClickPayload = {
  locationCode: string;
  x: number;
  y: number;
  gridRow?: number;
  rowLocationCodes?: string[];
  gridColumn?: number;
  columnLocationCodes?: string[];
};

type MapNode = {
  x: number;
  y: number;
  content: string;
};

type Props = {
  /** 1 zone hoặc danh sách zone cần vẽ chung trên cùng canvas. */
  zoneId: number | number[];
  showInboundSeparator?: boolean;
  className?: string;
  selectedCodes?: string[];
  onBufferCellClick?: (payload: BufferCellClickPayload) => void;
  onBufferCellDoubleClick?: (payload: BufferCellClickPayload) => void;
  tuning?: BufferMapCanvasTuning;
  /** Label overlay theo mã ô (vd. biển số xe / tên KH trên sorting station). */
  overlayLabelByCode?: Record<string, string>;
  /**
   * Chỉ các mã location trong danh sách này mới nhận được click.
   * Nếu không truyền → tất cả ô đều có thể click.
   */
  interactiveCodes?: string[] | Set<string>;
  /** Đường dẫn ảnh nền bản đồ (mặc định /maps/ALK_CNC_floor_1_08_11.png) */
  backgroundImageUrl?: string;
  /** Cho phép ẩn nút chọn ảnh nền nếu không cần */
  showBackgroundPicker?: boolean;
};

function drawInboundSeparator(
  ctx: CanvasRenderingContext2D,
  nodes: MapNode[],
  labelByCode: Map<string, LocationStockLabel>,
  shelfHalf: number,
  invScale: number,
) {
  const sortedNodes = [...nodes].sort((a, b) => a.x - b.x);
  const columns: { x: number; isBP: boolean; isCN: boolean }[] = [];
  for (const node of sortedNodes) {
    if (columns.length === 0 || node.x - columns[columns.length - 1].x > shelfHalf) {
      columns.push({ x: node.x, isBP: false, isCN: false });
    }
    const currentCol = columns[columns.length - 1];
    const bin = labelByCode.get(node.content)?.bin ?? "";
    if (bin.includes("BP")) currentCol.isBP = true;
    if (bin.includes("CN")) currentCol.isCN = true;
  }

  const allY = nodes.map((n) => n.y);
  const minY = Math.min(...allY) - shelfHalf;
  const maxY = Math.max(...allY) + shelfHalf;

  ctx.save();
  ctx.beginPath();
  ctx.strokeStyle = "rgba(100, 116, 139, 0.8)";
  ctx.lineWidth = 4 * invScale;
  for (let i = 0; i < columns.length - 1; i++) {
    const col1 = columns[i];
    const col2 = columns[i + 1];
    if (
      (col1.isBP && col2.isCN && !col1.isCN && !col2.isBP) ||
      (col1.isCN && col2.isBP && !col1.isBP && !col2.isCN)
    ) {
      const separatorX = (col1.x + col2.x) / 2;
      ctx.moveTo(separatorX, minY);
      ctx.lineTo(separatorX, maxY);
    }
  }
  ctx.stroke();
  ctx.restore();
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function OperatorMapCanvas({
  zoneId,
  showInboundSeparator = false,
  className,
  selectedCodes,
  onBufferCellClick,
  onBufferCellDoubleClick,
  tuning,
  overlayLabelByCode,
  interactiveCodes,
  backgroundImageUrl,
  showBackgroundPicker = true,
}: Props) {
  // ── Background Image State ──────────────────────────────────────────────────
  const [bgSrc, setBgSrc] = useState<string>(backgroundImageUrl || DEFAULT_BG_URL);
  const bgImageRef = useRef<HTMLImageElement | null>(null);
  const bgDimensionsRef = useRef<{ width: number; height: number }>({
    width: 3990,
    height: 1914,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync backgroundImageUrl prop if changed externally
  useEffect(() => {
    if (backgroundImageUrl) {
      setBgSrc(backgroundImageUrl);
    }
  }, [backgroundImageUrl]);

  // ── API data ────────────────────────────────────────────────────────────────
  const zoneIdsKey = (Array.isArray(zoneId) ? zoneId : [zoneId]).join(",");
  const zoneIds = useMemo(
    () =>
      [...new Set(zoneIdsKey.split(",").map(Number))]
        .filter((id) => Number.isFinite(id) && id > 0)
        .sort((a, b) => a - b),
    [zoneIdsKey],
  );

  const layoutQuery = useZonesMapLayout(zoneIds);
  const statusQuery = useZonesMapStatus(zoneIds);
  const layoutNodes = layoutQuery.items;

  const isLoading = layoutQuery.isLoading || statusQuery.isLoading;
  const failedZoneIds = useMemo(
    () => [...new Set([...layoutQuery.failedZoneIds, ...statusQuery.failedZoneIds])].sort((a, b) => a - b),
    [layoutQuery.failedZoneIds, statusQuery.failedZoneIds],
  );

  useEffect(() => {
    if (failedZoneIds.length > 0) {
      console.warn(`[OperatorMapCanvas] Không tải được zone: ${failedZoneIds.join(", ")}`);
    }
  }, [failedZoneIds]);

  // ── Derived data ────────────────────────────────────────────────────────────
  const labelByCode = useMemo(() => {
    const map = new Map<string, LocationStockLabel>();
    for (const cell of statusQuery.items) {
      let qty = 0;
      for (const item of cell.item_stock ?? []) {
        qty += Number(item.quantity) || 0;
      }
      map.set(cell.location_code, {
        location_id: cell.id,
        location_code: cell.location_code,
        is_empty: (cell.item_stock ?? []).length === 0,
        display_status: cell.status,
        product_sku: cell.item_stock?.[0]?.sku ?? null,
        product_name: cell.item_stock?.[0]?.sku ?? null,
        bin: cell.bin_code ?? null,
        location_type: null,
        quantity: qty,
        line_count: (cell.item_stock ?? []).length,
        lot_number: cell.item_stock?.[0]?.lot_number ?? null,
      });
    }
    return map;
  }, [statusQuery.items]);

  const interactiveCodeSet = useMemo(() => {
    if (interactiveCodes == null) return null;
    if (interactiveCodes instanceof Set) return interactiveCodes;
    return new Set(interactiveCodes);
  }, [interactiveCodes]);

  // ── Refs ────────────────────────────────────────────────────────────────────
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<MapNode[]>([]);
  const layoutNodesRef = useRef<ZoneMapLayoutNode[]>([]);
  const contentBoundsRef = useRef<MapContentBounds | null>(null);

  const labelByCodeRef = useRef<Map<string, LocationStockLabel>>(new Map());
  const overlayLabelByCodeRef = useRef<Record<string, string>>({});
  const selectedCodesRef = useRef<Set<string>>(new Set());
  const interactiveCodesRef = useRef<Set<string> | null>(null);

  const onClickRef = useRef(onBufferCellClick);
  const onDoubleClickRef = useRef(onBufferCellDoubleClick);

  const scaleRef = useRef(1);
  const offsetXRef = useRef(0);
  const offsetYRef = useRef(0);

  // Pan interaction refs
  const isPanningRef = useRef(false);
  const hasDraggedRef = useRef(false);
  const panStartRef = useRef({ x: 0, y: 0 });
  const lastMouseRef = useRef({ x: 0, y: 0 });

  const tuningRef = useRef<Required<BufferMapCanvasTuning>>({
    ...OPERATOR_MAP_CANVAS_DEFAULTS,
    fitPaddingRatio: 0.04,
    fitScaleFactor: 0.96,
  });

  tuningRef.current = {
    fitScaleFactor: tuning?.fitScaleFactor ?? 0.96,
    fitPaddingRatio: tuning?.fitPaddingRatio ?? 0.04,
    baseNodeSize: tuning?.baseNodeSize ?? OPERATOR_MAP_CANVAS_DEFAULTS.baseNodeSize,
    shelfSizeFactor: tuning?.shelfSizeFactor ?? OPERATOR_MAP_CANVAS_DEFAULTS.shelfSizeFactor,
    labelTextScale: tuning?.labelTextScale ?? OPERATOR_MAP_CANVAS_DEFAULTS.labelTextScale,
  };

  const [hasData, setHasData] = useState(false);

  // ── Helpers ─────────────────────────────────────────────────────────────────
  const isInteractiveCode = useCallback((code: string) => {
    const allowed = interactiveCodesRef.current;
    if (allowed == null) return true;
    return allowed.has(code);
  }, []);

  // ── Draw ────────────────────────────────────────────────────────────────────
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const opts = tuningRef.current;
    const labels = labelByCodeRef.current;
    const selectedCodes = selectedCodesRef.current;
    const invScale = 1 / scaleRef.current;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    ctx.setTransform(
      scaleRef.current, 0,
      0, scaleRef.current,
      offsetXRef.current, offsetYRef.current,
    );

    // 1. Vẽ Background Image nếu đã tải
    if (bgImageRef.current && bgImageRef.current.complete && bgImageRef.current.naturalWidth > 0) {
      ctx.drawImage(
        bgImageRef.current,
        0,
        0,
        bgDimensionsRef.current.width,
        bgDimensionsRef.current.height,
      );
    }

    // 2. Kích thước ô kệ trong world space (pixel)
    const baseNodePx =
      opts.baseNodeSize > 100
        ? opts.baseNodeSize * SCALE_MM_TO_PX
        : opts.baseNodeSize;
    const shelfHalf = baseNodePx * opts.shelfSizeFactor;
    const showLabels = shelfHalf * 2 * scaleRef.current >= LABEL_MIN_SCREEN_PX;

    // Vẽ đường phân cách BP / CN nếu bật
    if (showInboundSeparator && nodesRef.current.length > 0) {
      drawInboundSeparator(ctx, nodesRef.current, labels, shelfHalf, invScale);
    }

    // 3. Vẽ từng node ô kệ / station
    for (const node of nodesRef.current) {
      const interactive = isInteractiveCode(node.content);
      const isSelected = interactive && selectedCodes.has(node.content);
      const label = labels.get(node.content);
      const status = label?.display_status ?? "empty";
      const isFull = label != null && !label.is_empty;

      // Vẽ ô kệ với màu theo trạng thái
      drawShelfByStatus(ctx, status, isFull, node.x, node.y, shelfHalf, invScale);

      // Viền nổi bật khi đang được chọn
      if (isSelected) {
        drawSelectedHighlight(ctx, node.x, node.y, shelfHalf, invScale);
      }

      // Text label (SKU, số lượng, bin code)
      if (showLabels) {
        const overlay = overlayLabelByCodeRef.current[node.content]?.trim();
        const displayBin = label ? formatDisplayBin(label.bin, label.location_type) : "";

        if (overlay) {
          drawStationOverlayLabel(ctx, node.x, node.y, shelfHalf, overlay, isSelected, displayBin);
        } else {
          drawShelfStockLabel(
            ctx,
            node.x,
            node.y,
            shelfHalf,
            label,
            opts.labelTextScale,
            isSelected,
            false,
          );
        }
      }
    }

    ctx.restore();
  }, [showInboundSeparator, isInteractiveCode]);

  // ── Fit ─────────────────────────────────────────────────────────────────────
  const fitToCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const bounds = contentBoundsRef.current;
    if (!canvas || !bounds) return;
    const opts = tuningRef.current;

    const cW = Math.max(canvas.width, 300);
    const cH = Math.max(canvas.height, 150);
    const pad = Math.min(cW, cH) * opts.fitPaddingRatio;
    const availW = Math.max(cW - pad * 2, 20);
    const availH = Math.max(cH - pad * 2, 20);
    const bW = Math.max(bounds.width, 1);
    const bH = Math.max(bounds.height, 1);

    const scale = Math.min(availW / bW, availH / bH);
    const lockedScale = Math.max(scale * opts.fitScaleFactor, 0.001);
    scaleRef.current = lockedScale;
    offsetXRef.current = pad + (availW - bW * lockedScale) / 2 - bounds.minX * lockedScale;
    offsetYRef.current = pad + (availH - bH * lockedScale) / 2 - bounds.minY * lockedScale;
  }, []);

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const rect = container.getBoundingClientRect();
    const w = Math.round(rect.width) || container.clientWidth || 800;
    const h = Math.round(rect.height) || container.clientHeight || 600;
    canvas.width = Math.max(w, 1);
    canvas.height = Math.max(h, 1);
    fitToCanvas();
    draw();
  }, [draw, fitToCanvas]);

  // ── Node Alignment ──────────────────────────────────────────────────────────
  const refreshNodes = useCallback(() => {
    const raw = layoutNodesRef.current;
    const bgH = bgDimensionsRef.current.height;

    if (raw.length === 0) {
      nodesRef.current = [];
      if (bgDimensionsRef.current.width > 0 && bgH > 0) {
        contentBoundsRef.current = {
          minX: 0,
          minY: 0,
          maxX: bgDimensionsRef.current.width,
          maxY: bgH,
          width: bgDimensionsRef.current.width,
          height: bgH,
        };
        setHasData(true);
      } else {
        contentBoundsRef.current = null;
        setHasData(false);
      }
      fitToCanvas();
      draw();
      return;
    }

    // Tọa độ thực tế 1:1 theo hệ quy chiếu KUKA AMR:
    // x = map_x * 0.02 (1 px = 50 mm)
    // y = bgHeight - (map_y * 0.02)
    const nodes: MapNode[] = raw.map((n) => ({
      x: n.map_x * SCALE_MM_TO_PX,
      y: bgH - n.map_y * SCALE_MM_TO_PX,
      content: n.location_code,
    }));

    nodesRef.current = nodes;
    contentBoundsRef.current = {
      minX: 0,
      minY: 0,
      maxX: bgDimensionsRef.current.width,
      maxY: bgH,
      width: bgDimensionsRef.current.width,
      height: bgH,
    };

    setHasData(true);
    fitToCanvas();
    draw();
  }, [draw, fitToCanvas]);

  // Load Background Image
  useEffect(() => {
    if (!bgSrc) return;
    const img = new Image();
    img.src = bgSrc;
    img.onload = () => {
      bgImageRef.current = img;
      bgDimensionsRef.current = {
        width: img.naturalWidth || 3990,
        height: img.naturalHeight || 1914,
      };
      refreshNodes();
    };
    img.onerror = (err) => {
      console.warn(`[OperatorMapCanvas] Không tải được ảnh nền từ ${bgSrc}`, err);
    };
  }, [bgSrc, refreshNodes]);

  // Handle local background image upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const objectUrl = URL.createObjectURL(file);
      setBgSrc(objectUrl);
    }
  };

  // ── Effects ─────────────────────────────────────────────────────────────────
  useEffect(() => { onClickRef.current = onBufferCellClick; }, [onBufferCellClick]);
  useEffect(() => { onDoubleClickRef.current = onBufferCellDoubleClick; }, [onBufferCellDoubleClick]);

  useEffect(() => {
    labelByCodeRef.current = labelByCode;
    draw();
  }, [labelByCode, draw]);

  useEffect(() => {
    overlayLabelByCodeRef.current = overlayLabelByCode ?? {};
    draw();
  }, [overlayLabelByCode, draw]);

  useEffect(() => {
    interactiveCodesRef.current = interactiveCodeSet;
    draw();
  }, [interactiveCodeSet, draw]);

  useEffect(() => {
    if (selectedCodes && selectedCodes.length > 0) {
      selectedCodesRef.current = new Set(selectedCodes);
    } else {
      selectedCodesRef.current = new Set();
    }
    draw();
  }, [selectedCodes, draw]);

  useEffect(() => {
    if (layoutQuery.isLoading) return;
    layoutNodesRef.current = layoutNodes;
    refreshNodes();
  }, [layoutQuery.isLoading, layoutNodes, refreshNodes]);

  // ResizeObserver
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => resizeCanvas());
    observer.observe(container);
    resizeCanvas();
    return () => observer.disconnect();
  }, [resizeCanvas]);

  // ── Zoom (Wheel) ────────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;

      const factor = e.deltaY < 0 ? ZOOM_FACTOR : 1 / ZOOM_FACTOR;
      const newScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, scaleRef.current * factor));

      const wx = (cx - offsetXRef.current) / scaleRef.current;
      const wy = (cy - offsetYRef.current) / scaleRef.current;

      scaleRef.current = newScale;
      offsetXRef.current = cx - wx * newScale;
      offsetYRef.current = cy - wy * newScale;

      draw();
    };

    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [draw]);

  // ── Pan & Click Handling ────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      isPanningRef.current = true;
      hasDraggedRef.current = false;
      panStartRef.current = { x: e.clientX, y: e.clientY };
      lastMouseRef.current = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isPanningRef.current) return;
      const dx = e.clientX - lastMouseRef.current.x;
      const dy = e.clientY - lastMouseRef.current.y;

      const dist = Math.hypot(
        e.clientX - panStartRef.current.x,
        e.clientY - panStartRef.current.y,
      );
      if (dist > 4) {
        hasDraggedRef.current = true;
        canvas.style.cursor = "grabbing";
      }

      offsetXRef.current += dx;
      offsetYRef.current += dy;
      lastMouseRef.current = { x: e.clientX, y: e.clientY };
      draw();
    };

    const onMouseUp = () => {
      isPanningRef.current = false;
      canvas.style.cursor =
        onClickRef.current || onDoubleClickRef.current ? "pointer" : "default";
    };

    const resolveClickPayload = (e: MouseEvent): BufferCellClickPayload | null => {
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const wx = (sx - offsetXRef.current) / scaleRef.current;
      const wy = (sy - offsetYRef.current) / scaleRef.current;

      const opts = tuningRef.current;
      const baseNodePx =
        opts.baseNodeSize > 100
          ? opts.baseNodeSize * SCALE_MM_TO_PX
          : opts.baseNodeSize;
      const shelfHalf = baseNodePx * opts.shelfSizeFactor;
      const hitRadius = Math.max(shelfHalf * 0.9, 12 / scaleRef.current);
      let closest: MapNode | null = null;
      let closestDist = Infinity;

      for (const node of nodesRef.current) {
        if (!isInteractiveCode(node.content)) continue;
        const dist = Math.hypot(wx - node.x, wy - node.y);
        if (dist <= hitRadius && dist < closestDist) {
          closestDist = dist;
          closest = node;
        }
      }
      if (!closest) return null;

      const columnLocationCodes = nodesRef.current
        .filter((n) => Math.abs(n.x - closest!.x) < shelfHalf * 0.8)
        .map((n) => n.content);

      return {
        locationCode: closest.content,
        x: closest.x,
        y: closest.y,
        columnLocationCodes,
      };
    };

    const onClick = (e: MouseEvent) => {
      if (hasDraggedRef.current) return;
      const payload = resolveClickPayload(e);
      if (payload) onClickRef.current?.(payload);
    };

    const onDoubleClick = (e: MouseEvent) => {
      if (hasDraggedRef.current) return;
      if (!onDoubleClickRef.current) return;
      const payload = resolveClickPayload(e);
      if (payload) onDoubleClickRef.current(payload);
    };

    canvas.addEventListener("mousedown", onMouseDown);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("click", onClick);
    canvas.addEventListener("dblclick", onDoubleClick);

    canvas.style.cursor =
      onClickRef.current || onDoubleClickRef.current ? "pointer" : "default";

    return () => {
      canvas.removeEventListener("mousedown", onMouseDown);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("click", onClick);
      canvas.removeEventListener("dblclick", onDoubleClick);
    };
  }, [draw, isInteractiveCode]);

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div
      ref={containerRef}
      className={`relative min-h-0 w-full overflow-hidden bg-canvas ${className ?? ""}`}
    >
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />

      {/* Nút đổi ảnh nền gọn gàng ở góc trên bên phải */}
      {showBackgroundPicker && (
        <div className="absolute top-3 right-3 z-10">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200/80 bg-white/90 px-2.5 py-1.5 text-xs font-medium text-slate-700 shadow-sm backdrop-blur-sm transition-colors hover:bg-white hover:text-slate-900"
            title="Đổi ảnh nền bản đồ (PNG, JPG)"
          >
            <svg
              className="h-3.5 w-3.5 text-slate-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <span>Đổi ảnh nền</span>
          </button>
        </div>
      )}

      {isLoading && (
        <div className="pointer-events-none absolute left-3 bottom-3 flex items-center gap-2 rounded-lg bg-white/90 px-3 py-1.5 text-xs text-slate-500 shadow-sm border border-slate-200">
          <div className="h-3 w-3 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
          <span>Đang tải dữ liệu node...</span>
        </div>
      )}

      {!isLoading && !hasData && failedZoneIds.length > 0 && (
        <div className="pointer-events-none absolute left-3 bottom-3 rounded-lg bg-amber-50/95 px-3 py-1.5 text-xs text-amber-700 shadow-sm border border-amber-200">
          Chưa kết nối dữ liệu zone {failedZoneIds.join(", ")}
        </div>
      )}

      {!isLoading && hasData && failedZoneIds.length > 0 && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-amber-50/95 px-3 py-1.5 text-xs text-amber-700 shadow-sm border border-amber-200">
          Không tải được zone {failedZoneIds.join(", ")}
        </div>
      )}

      {!isLoading && failedZoneIds.length === 0 && hasData && labelByCode.size === 0 && (
        <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg bg-white/90 px-3 py-1.5 text-xs text-slate-500 shadow-sm border border-slate-200">
          Chưa có điểm nào trên bản đồ
        </div>
      )}
    </div>
  );
}
