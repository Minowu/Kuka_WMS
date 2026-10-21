/**
 * WarehouseMapCanvas
 *
 * Production-grade interactive warehouse map renderer using HTML5 Canvas.
 *
 * Features:
 *  - Loads map data from backend API via React Query
 *  - Automatically re-fetches when the selected zone changes (Zustand → queryKey)
 *  - Renderable locations API determines full/empty shelf status
 *  - Zoom centred on cursor (mousewheel) with configurable min/max
 *  - Smooth pan (left-button drag)
 *  - Lines drawn exclusively from the `path` array (index 6 of lineArr)
 *  - Nodes: type=0 → small grey circle | type=1 → hatched square (shelf)
 *  - Node sizes are screen-constant (baseSize / scale) — never blow up on zoom
 *  - Click detection via inverse-transform → Euclidean distance (hitRadius)
 *  - Diagonal hatch pattern for shelves is generated once and cached
 *  - Admin can import new map ZIP via import dialog
 */

import React, {
  useRef,
  useEffect,
  useCallback,
  useState,
  useMemo,
} from 'react';
import WarehouseMapDrawer from './WarehouseMapDrawer';
import WarehouseMapImportDialog from './WarehouseMapImportDialog';
import WarehouseMapToolbar from './WarehouseMapToolbar';
import WarehouseMapOverlays from './WarehouseMapOverlays';
import WarehouseMapLegend from './WarehouseMapLegend';
import WarehouseMapZoomControls from './WarehouseMapZoomControls';
import { useAppStore } from '@/store/useAppStore';
import { useAuthStore } from '@/store/useAuthStore';

import { useActiveWarehouseMap, useFullLocations, useDownloadWarehouseMap } from '@/hooks/useWarehouseMap';
import { message } from '@/components/ui';
import type { MapData, NodeInfo, FullLocationDetail } from '@/types/warehouseMap';
import { formatQuantity } from '@/utils/formatQuantity';
import { getApiErrorMessage } from '@/utils/apiErrorMessage';
import {
  ZOOM_MAX,
  ZOOM_FACTOR,
  HIT_RADIUS,
  BASE_NODE_SIZE,
  LINE_COLOR,
  NODE_NORMAL_COLOR,
  SHELF_FULL_COLOR,
  SHELF_EMPTY_COLOR,
  SHELF_RESERVED_COLOR,
  SHELF_IN_TRANSIT_COLOR,
  SHELF_SELECTED_COLOR,
  SHELF_STROKE_COLOR,
  SHELF_SELECTED_STROKE_COLOR,
  PADDING,
  BOX_SELECT_DRAG_THRESHOLD,
  BOX_SELECT_FILL,
  BOX_SELECT_STROKE,
  getShelfNodesInWorldRect,
  parseNode,
} from '@/utils/warehouseMapUtils';

// ─── Props ──────────────────────────────────────────────────────────────────────

interface WarehouseMapCanvasProps {
  /** Callback khi user click vào một node trên bản đồ. Trả về null nếu click vào khoảng trống. */
  onNodeClick?: (node: NodeInfo | null) => void;
  /** Ẩn thanh toolbar (dùng khi nhúng làm Picker) */
  hideToolbar?: boolean;
  /** Ẩn drawer chi tiết khi click vào kệ (dùng khi nhúng làm Picker) */
  hideDrawer?: boolean;
  /** Mã location đang được chọn — highlight màu xanh trên map */
  selectedLocationCodes?: string[];
  /** Ghi đè warehouse đang chọn trên header (vd. map kiểm kê theo phiếu). */
  warehouseId?: number;
  /** Dữ liệu vị trí/tồn tùy chỉnh — dùng cho map kiểm kê thay API full-locations. */
  locationOverrides?: FullLocationDetail[];
  /** Bỏ gọi API preview/full-locations; chỉ dùng locationOverrides. */
  skipFullLocationsFetch?: boolean;
  /** Bật kéo vùng chọn nhiều điểm (picker mode). */
  enableBoxSelect?: boolean;
  /** Khi true, kéo chuột trái vẽ vùng chọn thay vì pan. */
  boxSelectActive?: boolean;
  /** Callback khi hoàn tất kéo vùng — trả về các shelf node trong vùng. */
  onBoxSelect?: (nodes: NodeInfo[]) => void;
}


// ─── Component ─────────────────────────────────────────────────────────────────

const WarehouseMapCanvas: React.FC<WarehouseMapCanvasProps> = ({
  onNodeClick,
  hideToolbar = false,
  hideDrawer = false,
  selectedLocationCodes = [],
  warehouseId: warehouseIdProp,
  locationOverrides,
  skipFullLocationsFetch = false,
  enableBoxSelect = false,
  boxSelectActive = false,
  onBoxSelect,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // ─── Zustand stores ────────────────────────────────────────────────────────
  const selectedWarehouseId = useAppStore((s) => s.selectedWarehouseId);
  const resolvedWarehouseId = warehouseIdProp ?? selectedWarehouseId;
  const user = useAuthStore((s) => s.user);
  const isAdmin = !!user?.access?.is_admin;

  // ─── React Query hooks ─────────────────────────────────────────────────────
  const {
    data: mapApiData,
    isLoading,
    isError,
    error,
  } = useActiveWarehouseMap(resolvedWarehouseId);

  const { data: fullLocationsData, refetch: refetchFullLocations } =
    useFullLocations(skipFullLocationsFetch ? 0 : resolvedWarehouseId);

  const effectiveLocations = useMemo(() => {
    if (locationOverrides) {
      return {
        location_codes: locationOverrides
          .filter((loc) => loc.item_stock.length > 0)
          .map((loc) => loc.location_code),
        locations: locationOverrides,
      };
    }
    return {
      location_codes: fullLocationsData?.location_codes ?? [],
      locations: fullLocationsData?.locations ?? [],
    };
  }, [locationOverrides, fullLocationsData]);

  const fullLocationCodes = useMemo(
    () => new Set(effectiveLocations.location_codes),
    [effectiveLocations.location_codes],
  );

  // Map data (parsed once per API response, never mutated)
  const mapDataRef = useRef<MapData | null>(null);
  const nodesRef = useRef<NodeInfo[]>([]);
  const fullCodesRef = useRef<Set<string>>(new Set());
  const fullLocationsMapRef = useRef<Map<string, FullLocationDetail>>(new Map());
  const selectedCodesRef = useRef<Set<string>>(new Set());

  const selectedCodesKey = useMemo(
    () => selectedLocationCodes.join('\u0000'),
    [selectedLocationCodes],
  );

  useEffect(() => {
    selectedCodesRef.current = new Set(
      selectedLocationCodes.map((code) => String(code)),
    );
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCodesKey]);

  // Keep fullCodesRef in sync
  useEffect(() => {
    fullCodesRef.current = fullLocationCodes;
    
    const map = new Map<string, FullLocationDetail>();
    if (effectiveLocations.locations) {
      for (const loc of effectiveLocations.locations) {
        if (loc.location_code) {
          map.set(loc.location_code, loc);
        }
        if (loc.location_label) {
          map.set(loc.location_label, loc);
        }
        if (loc.location_name) {
          map.set(loc.location_name, loc);
        }
      }
    }
    fullLocationsMapRef.current = map;

    // Re-draw when renderable locations change
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullLocationCodes, effectiveLocations]);

  // Transform state (mutable refs — no re-render needed for every frame)
  const scaleRef = useRef(1);
  const offsetXRef = useRef(0);
  const offsetYRef = useRef(0);

  // Dynamic zoom floor — updated after each fitToCanvas() call so the user
  // can always scroll back to the initial overview, even for huge maps.
  const zoomMinRef = useRef(0.001);

  // Pan state
  const isPanningRef = useRef(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });

  // Box-select state
  const isBoxSelectingRef = useRef(false);
  const boxStartScreenRef = useRef({ x: 0, y: 0 });
  const boxEndScreenRef = useRef({ x: 0, y: 0 });
  const suppressNextClickRef = useRef(false);
  const boxSelectActiveRef = useRef(boxSelectActive);
  const enableBoxSelectRef = useRef(enableBoxSelect);

  useEffect(() => {
    boxSelectActiveRef.current = boxSelectActive;
    enableBoxSelectRef.current = enableBoxSelect;
    if (canvasRef.current) {
      canvasRef.current.style.cursor = boxSelectActive ? 'crosshair' : 'grab';
    }
  }, [boxSelectActive, enableBoxSelect]);

  // UI state
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [selectedNode, setSelectedNode] = useState<NodeInfo | null>(null);
  const [selectedLocationId, setSelectedLocationId] = useState<number | undefined>();
  const [detailRefreshToken, setDetailRefreshToken] = useState(0);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // Download mutation
  const downloadMutation = useDownloadWarehouseMap();

  // ─── Draw ───────────────────────────────────────────────────────────────────

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const mapData = mapDataRef.current;
    if (!mapData) return;

    const { width: W, height: H } = canvas;
    ctx.clearRect(0, 0, W, H);

    // Apply camera transform
    ctx.save();
    ctx.setTransform(scaleRef.current, 0, 0, scaleRef.current, offsetXRef.current, offsetYRef.current);

    const invScale = 1 / scaleRef.current;

    // ── Draw Lines ────────────────────────────────────────────────────────────
    ctx.beginPath();
    ctx.strokeStyle = LINE_COLOR;
    ctx.lineWidth = invScale * 2; // screen-constant 2px line

    for (const lineRow of mapData.lineArr) {
      // path is always at index 6 per lineKeys spec
      const rawPath = lineRow[6];
      if (!rawPath || !Array.isArray(rawPath) || rawPath.length === 0) continue;

      // ── Auto-detect path format ──────────────────────────────────────────
      // Format A (nested): [[x0,y0], [x1,y1], ...]
      // Format B (flat):   [x0, y0, x1, y1, ...]
      let coords: { x: number; y: number }[] = [];

      if (Array.isArray(rawPath[0])) {
        // Format A — each element is a [x, y] pair
        for (const pt of rawPath as unknown as number[][]) {
          if (pt && pt.length >= 2 && pt[0] != null && pt[1] != null) {
            // Y-flip for path coordinates: same rule as nodes
            coords.push({ x: pt[0], y: mapData.height - pt[1] });
          }
        }
      } else {
        // Format B — flat array [x0, y0, x1, y1, ...], filter nulls first
        const pts = (rawPath as (number | null)[]).filter(
          (v): v is number => v != null && typeof v === 'number',
        );
        // Must be even (x,y pairs)
        const len = pts.length % 2 === 0 ? pts.length : pts.length - 1;
        for (let i = 0; i < len; i += 2) {
          // Y-flip for path coordinates: same rule as nodes
          coords.push({ x: pts[i], y: mapData.height - pts[i + 1] });
        }
      }

      if (coords.length < 2) continue;

      ctx.moveTo(coords[0].x, coords[0].y);
      for (let i = 1; i < coords.length; i++) {
        ctx.lineTo(coords[i].x, coords[i].y);
      }
    }
    ctx.stroke();

    // ── Draw Nodes ────────────────────────────────────────────────────────────
    const baseSize = BASE_NODE_SIZE;

    for (const node of nodesRef.current) {
      const { x, y, type } = node;
      const locDetail =
        fullLocationsMapRef.current.get(node.content) ||
        fullLocationsMapRef.current.get(node.name);

      const isStation = Boolean(
        type === 1 ||
          (locDetail && locDetail.location_type && locDetail.location_type !== 'UNASSIGNED')
      );

      if (!isStation) {
        // Normal waypoint: small grey circle
        ctx.beginPath();
        ctx.arc(x, y, baseSize * 0.3, 0, Math.PI * 2);
        ctx.fillStyle = NODE_NORMAL_COLOR;
        ctx.fill();
      } else {
        const half = baseSize * 0.7;
        const isSelected =
          selectedCodesRef.current.has(String(node.content)) ||
          (locDetail && selectedCodesRef.current.has(String(locDetail.location_code)));

        const hasActiveStock = Boolean(
          (locDetail?.item_stock && locDetail.item_stock.length > 0) ||
            locDetail?.container_code ||
            locDetail?.status === 'has_stock'
        );

        const isFull =
          fullCodesRef.current.has(node.content) ||
          fullCodesRef.current.has(node.name) ||
          (locDetail && fullCodesRef.current.has(locDetail.location_code)) ||
          hasActiveStock;

        const locationStatus = locDetail?.status;
        const isReserved = locationStatus === 'reserved';
        const isInTransit = locationStatus === 'in_transit';

        if (isSelected) {
          ctx.fillStyle = SHELF_SELECTED_COLOR;
        } else if (isReserved) {
          ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
        } else if (isInTransit) {
          ctx.fillStyle = 'rgba(59, 130, 246, 0.25)';
        } else if (isFull || locationStatus === 'has_stock') {
          ctx.fillStyle = SHELF_FULL_COLOR;
        } else {
          ctx.fillStyle = SHELF_EMPTY_COLOR;
        }
        ctx.fillRect(x - half * 1.5, y - half, half * 3, half * 2);

        if (isReserved) {
          ctx.save();
          ctx.setLineDash([invScale * 6, invScale * 3]);
          ctx.strokeStyle = '#d97706';
          ctx.lineWidth = invScale * 1.6;
          ctx.strokeRect(x - half * 1.5, y - half, half * 3, half * 2);
          ctx.restore();
        } else if (isInTransit) {
          ctx.save();
          ctx.setLineDash([invScale * 4, invScale * 2]);
          ctx.strokeStyle = '#2563eb';
          ctx.lineWidth = invScale * 1.4;
          ctx.strokeRect(x - half * 1.5, y - half, half * 3, half * 2);
          ctx.restore();
        } else {
          ctx.strokeStyle = isSelected ? SHELF_SELECTED_STROKE_COLOR : (isFull ? '#059669' : SHELF_STROKE_COLOR);
          ctx.lineWidth = invScale * (isSelected ? 1.4 : 1.0);
          ctx.strokeRect(x - half * 1.5, y - half, half * 3, half * 2);
        }

        const maxTextWidth = half * 2.8;
        const stationTitle = locDetail?.location_name || node.name || node.content;

        if (isReserved && !isSelected) {
          ctx.save();
          ctx.fillStyle = '#b45309';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          const fontSize = half * 0.28;
          ctx.font = '700 ' + fontSize + 'px sans-serif';
          ctx.fillText('GIU CHO', x, y - fontSize * 0.6, maxTextWidth);
          ctx.font = '500 ' + (fontSize * 0.85) + 'px sans-serif';
          ctx.fillStyle = '#d97706';
          ctx.fillText(stationTitle, x, y + fontSize * 0.7, maxTextWidth);
          ctx.restore();
        } else if (isInTransit && !isSelected) {
          ctx.save();
          ctx.fillStyle = '#1d4ed8';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          const fontSize = half * 0.28;
          ctx.font = '700 ' + fontSize + 'px sans-serif';
          ctx.fillText('DANG CHUYEN', x, y - fontSize * 0.6, maxTextWidth);
          ctx.font = '500 ' + (fontSize * 0.85) + 'px sans-serif';
          ctx.fillStyle = '#2563eb';
          ctx.fillText(locDetail?.container_code ? 'CONT: ' + locDetail.container_code : stationTitle, x, y + fontSize * 0.7, maxTextWidth);
          ctx.restore();
        } else if (isFull && !isSelected) {
          ctx.save();
          ctx.fillStyle = '#ffffff';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.shadowColor = 'rgba(0, 0, 0, 0.45)';
          ctx.shadowBlur = half * 0.1;

          const fontSize = half * 0.30;
          ctx.font = '600 ' + fontSize + 'px sans-serif';

          const stock = locDetail?.item_stock?.[0];
          const containerLabel = locDetail?.container_code ? 'CONT: ' + locDetail.container_code : (stock?.sku || 'CO HANG');
          const qtyText = stock ? 'Qty: ' + formatQuantity(stock.quantity, '0') : (stationTitle || 'Dang co phoi');

          ctx.fillText(containerLabel, x, y - fontSize * 0.6, maxTextWidth);
          ctx.font = '400 ' + (fontSize * 0.85) + 'px sans-serif';
          ctx.fillText(qtyText, x, y + fontSize * 0.8, maxTextWidth);
          ctx.restore();
        } else if (!isSelected) {
          ctx.save();
          ctx.fillStyle = '#64748b';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          const fontSize = half * 0.32;
          ctx.font = '500 ' + fontSize + 'px sans-serif';
          ctx.fillText(stationTitle, x, y, maxTextWidth);
          ctx.restore();
        }

      }
    }

    ctx.restore();

    // ── Selection box overlay (screen space) ─────────────────────────────────
    if (isBoxSelectingRef.current && enableBoxSelectRef.current) {
      const x1 = Math.min(boxStartScreenRef.current.x, boxEndScreenRef.current.x);
      const y1 = Math.min(boxStartScreenRef.current.y, boxEndScreenRef.current.y);
      const w = Math.abs(boxEndScreenRef.current.x - boxStartScreenRef.current.x);
      const h = Math.abs(boxEndScreenRef.current.y - boxStartScreenRef.current.y);

      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = BOX_SELECT_FILL;
      ctx.strokeStyle = BOX_SELECT_STROKE;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 4]);
      ctx.fillRect(x1, y1, w, h);
      ctx.strokeRect(x1, y1, w, h);
      ctx.restore();
    }
  }, []);

  // ─── Fit Map to Canvas ──────────────────────────────────────────────────────

  const fitToCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const mapData = mapDataRef.current;
    if (!canvas || !mapData) return;

    const { width: mapW, height: mapH } = mapData;
    const cW = canvas.width;
    const cH = canvas.height;

    const pad = Math.min(cW, cH) * PADDING;
    const availW = cW - pad * 2;
    const availH = cH - pad * 2;

    const scaleX = availW / mapW;
    const scaleY = availH / mapH;
    const scale = Math.min(scaleX, scaleY); // maintain aspect ratio

    scaleRef.current = scale;
    offsetXRef.current = pad + (availW - mapW * scale) / 2;
    offsetYRef.current = pad + (availH - mapH * scale) / 2;

    // Allow zooming back out to exactly the fit view (scale * 0.8 gives a tiny margin)
    zoomMinRef.current = scale * 0.8;
  }, []);

  // ─── Resize Observer ────────────────────────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ro = new ResizeObserver(() => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;

      if (mapDataRef.current) {
        fitToCanvas();
        draw();
      }
    });

    ro.observe(container);
    return () => ro.disconnect();
  }, [draw, fitToCanvas]);

  // ─── Apply map data to canvas (shared helper) ──────────────────────────────

  const applyMapData = useCallback(
    (data: MapData) => {
      if (!data.nodeArr || !data.lineArr) {
        return;
      }
      mapDataRef.current = data;
      const parsedNodes = data.nodeArr.map((row) => parseNode(row, data.height));
      nodesRef.current = parsedNodes;

      fitToCanvas();
      draw();
    },
    [draw, fitToCanvas],
  );

  // ─── React Query data → Canvas ─────────────────────────────────────────────
  // When API data arrives or changes (zone switch), apply it to the canvas.
  useEffect(() => {
    if (!mapApiData) return;
    applyMapData(mapApiData);
  }, [mapApiData, applyMapData]);

  // ─── Mouse → World coordinate conversion ────────────────────────────────────

  const screenToWorld = useCallback((sx: number, sy: number) => {
    return {
      wx: (sx - offsetXRef.current) / scaleRef.current,
      wy: (sy - offsetYRef.current) / scaleRef.current,
    };
  }, []);

  // ─── Canvas rect helper ──────────────────────────────────────────────────────

  const getCanvasPos = useCallback((e: MouseEvent | WheelEvent) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    return { cx: e.clientX - rect.left, cy: e.clientY - rect.top };
  }, []);

  const getShelfNodesInScreenRect = useCallback(
    (sx1: number, sy1: number, sx2: number, sy2: number) => {
      const topLeft = screenToWorld(Math.min(sx1, sx2), Math.min(sy1, sy2));
      const bottomRight = screenToWorld(Math.max(sx1, sx2), Math.max(sy1, sy2));

      return getShelfNodesInWorldRect(
        nodesRef.current,
        Math.min(topLeft.wx, bottomRight.wx),
        Math.max(topLeft.wx, bottomRight.wx),
        Math.min(topLeft.wy, bottomRight.wy),
        Math.max(topLeft.wy, bottomRight.wy),
      );
    },
    [screenToWorld],
  );

  // ─── Zoom (wheel + buttons) ───────────────────────────────────────────────────

  const applyZoom = useCallback(
    (zoomIn: boolean, pivotCx?: number, pivotCy?: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const cx = pivotCx ?? canvas.width / 2;
      const cy = pivotCy ?? canvas.height / 2;

      const factor = zoomIn ? ZOOM_FACTOR : 1 / ZOOM_FACTOR;
      const newScale = Math.min(
        ZOOM_MAX,
        Math.max(zoomMinRef.current, scaleRef.current * factor),
      );

      const { wx, wy } = screenToWorld(cx, cy);
      scaleRef.current = newScale;
      offsetXRef.current = cx - wx * newScale;
      offsetYRef.current = cy - wy * newScale;

      draw();
    },
    [draw, screenToWorld],
  );

  const handleZoomIn = useCallback(() => {
    applyZoom(true);
  }, [applyZoom]);

  const handleZoomOut = useCallback(() => {
    applyZoom(false);
  }, [applyZoom]);

  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      const { cx, cy } = getCanvasPos(e);
      applyZoom(e.deltaY < 0, cx, cy);
    },
    [applyZoom, getCanvasPos],
  );

  // ─── Pan ─────────────────────────────────────────────────────────────────────

  const handleMouseDown = useCallback(
    (e: MouseEvent) => {
      if (e.button !== 0) return;

      const useBoxSelect =
        enableBoxSelectRef.current &&
        (boxSelectActiveRef.current || e.shiftKey);

      if (useBoxSelect) {
        const { cx, cy } = getCanvasPos(e);
        isBoxSelectingRef.current = true;
        boxStartScreenRef.current = { x: cx, y: cy };
        boxEndScreenRef.current = { x: cx, y: cy };
        if (canvasRef.current) canvasRef.current.style.cursor = 'crosshair';
        return;
      }

      isPanningRef.current = true;
      lastMouseRef.current = { x: e.clientX, y: e.clientY };
      if (canvasRef.current) canvasRef.current.style.cursor = 'grabbing';
    },
    [getCanvasPos],
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (isBoxSelectingRef.current) {
        const { cx, cy } = getCanvasPos(e);
        boxEndScreenRef.current = { x: cx, y: cy };
        draw();
        return;
      }

      if (!isPanningRef.current) return;
      const dx = e.clientX - lastMouseRef.current.x;
      const dy = e.clientY - lastMouseRef.current.y;
      offsetXRef.current += dx;
      offsetYRef.current += dy;
      lastMouseRef.current = { x: e.clientX, y: e.clientY };
      draw();
    },
    [draw, getCanvasPos],
  );

  const handleMouseUp = useCallback(() => {
    if (isBoxSelectingRef.current) {
      const { x: sx1, y: sy1 } = boxStartScreenRef.current;
      const { x: sx2, y: sy2 } = boxEndScreenRef.current;
      const dragDx = Math.abs(sx2 - sx1);
      const dragDy = Math.abs(sy2 - sy1);

      isBoxSelectingRef.current = false;

      if (
        dragDx >= BOX_SELECT_DRAG_THRESHOLD ||
        dragDy >= BOX_SELECT_DRAG_THRESHOLD
      ) {
        suppressNextClickRef.current = true;
        const nodes = getShelfNodesInScreenRect(sx1, sy1, sx2, sy2);
        onBoxSelect?.(nodes);
      }

      if (canvasRef.current) {
        canvasRef.current.style.cursor = boxSelectActiveRef.current
          ? 'crosshair'
          : 'grab';
      }
      draw();
      return;
    }

    isPanningRef.current = false;
    if (canvasRef.current) {
      canvasRef.current.style.cursor = boxSelectActiveRef.current
        ? 'crosshair'
        : 'grab';
    }
  }, [draw, getShelfNodesInScreenRect, onBoxSelect]);

  // ─── Click → Hit Detection → Drawer ────────────────────────────────────────

  const handleClick = useCallback(
    (e: MouseEvent) => {
      if (!mapDataRef.current) return;

      if (suppressNextClickRef.current) {
        suppressNextClickRef.current = false;
        return;
      }

      const { cx, cy } = getCanvasPos(e);
      const { wx, wy } = screenToWorld(cx, cy);

      // hitRadius is in world coordinates — stays constant regardless of zoom
      // (a constant screen-space radius would be HIT_RADIUS / scaleRef.current)
      const hitRadiusWorld = HIT_RADIUS / scaleRef.current;

      let closest: NodeInfo | null = null;
      let closestDist = Infinity;

      for (const node of nodesRef.current) {
        const dx = wx - node.x;
        const dy = wy - node.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < hitRadiusWorld && dist < closestDist && node.type == 1) {
          closestDist = dist;
          closest = node;
        }
      }

      if (closest) {
        setSelectedNode(closest);
        const loc = fullLocationsMapRef.current.get(closest.content);
        setSelectedLocationId(loc?.id);
        if (!hideDrawer) setDrawerVisible(true);

        const isOverviewMode = !hideDrawer && !skipFullLocationsFetch;
        if (isOverviewMode) {
          void refetchFullLocations();
          setDetailRefreshToken((token) => token + 1);
        }

        // Picker mode (hideDrawer): luôn trả node cho parent.
        // Map view: chỉ callback khi kệ không full (giữ hành vi cũ).
        if (hideDrawer || !fullCodesRef.current.has(closest.content)) {
          onNodeClick?.(closest);
        }
      } else {
        setDrawerVisible(false);
        setSelectedLocationId(undefined);
        onNodeClick?.(null);
      }
    },
    [
      getCanvasPos,
      screenToWorld,
      hideDrawer,
      skipFullLocationsFetch,
      refetchFullLocations,
      onNodeClick,
    ],
  );

  // ─── Attach Canvas Event Listeners ──────────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.addEventListener('wheel', handleWheel, { passive: false });
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseUp);
    canvas.addEventListener('click', handleClick);

    canvas.style.cursor = 'grab';

    return () => {
      canvas.removeEventListener('wheel', handleWheel);
      canvas.removeEventListener('mousedown', handleMouseDown);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseup', handleMouseUp);
      canvas.removeEventListener('mouseleave', handleMouseUp);
      canvas.removeEventListener('click', handleClick);
    };
  }, [handleWheel, handleMouseDown, handleMouseMove, handleMouseUp, handleClick]);

  // ─── Derive UI state ──────────────────────────────────────────────────────

  const hasData = !!mapApiData;
  const nodesCount = mapApiData?.nodeArr?.length ?? 0;
  const linesCount = mapApiData?.lineArr?.length;
  const errorMessage = isError
    ? getApiErrorMessage(error, 'Không thể tải bản đồ')
    : null;

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full w-full font-sans">
      {/* ── Toolbar ── */}
      {!hideToolbar && (
        <WarehouseMapToolbar
          isAdmin={isAdmin}
          hasData={hasData}
          isLoading={isLoading}
          errorMessage={errorMessage}
          nodesCount={nodesCount}
          linesCount={linesCount}
          downloadLoading={downloadMutation.isPending}
          onImportClick={() => setImportDialogOpen(true)}
          onDownloadClick={() => {
            downloadMutation.mutate(
              { warehouseId: resolvedWarehouseId },
              {
                onSuccess: () => message.success('Đã tải xuống bản đồ'),
                onError: () => message.error('Không thể tải xuống bản đồ'),
              },
            );
          }}
        />
      )}

      {/* ── Canvas Area ── */}
      <div
        ref={containerRef}
        className="relative flex-1 overflow-hidden rounded-b-xl border border-slate-200 shadow-inner bg-transparent"
      >
        <canvas ref={canvasRef} className="absolute inset-0 block w-full h-full" />

        {/* Overlays: loading / error / full */}
        <WarehouseMapOverlays
          isLoading={isLoading}
          isError={isError}
          hasData={hasData}
          errorMessage={errorMessage}
          isAdmin={isAdmin}
        />

        {hasData && !isLoading && !isError && <WarehouseMapLegend />}

        {!hideToolbar && hasData && !isLoading && !isError && (
          <WarehouseMapZoomControls
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
          />
        )}

        {/* Drawer Component */}
        {!hideDrawer && (
          <WarehouseMapDrawer
            visible={drawerVisible}
            onClose={() => {
              setDrawerVisible(false);
              setSelectedLocationId(undefined);
            }}
            node={selectedNode}
            locationId={selectedLocationId}
            refreshToken={detailRefreshToken}
          />
        )}
      </div>

      {/* Import Dialog — admin only */}
      {!hideToolbar && isAdmin && (
        <WarehouseMapImportDialog
          open={importDialogOpen}
          onClose={() => setImportDialogOpen(false)}
          warehouseId={resolvedWarehouseId}
        />
      )}
    </div>
  );
};

export default WarehouseMapCanvas;
