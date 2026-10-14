/**
 * Board tab Xuất trực tiếp.
 * Form chọn + 2 map (nhập | chia chọn & cửa xuất).
 * Click map chỉ fill select — không mở popup; ô không BP/CX bị mờ và không chọn được.
 */
import { useEffect, useMemo, useState } from "react";
import {
  ExportOutlined,
  RobotOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { Button, Input, Modal, Select, message } from "@/components/ui";
import {
  OPERATOR_DESKTOP,
  OPERATOR_DIRECT_OUTBOUND_MAP_TUNING,
} from "@/constants/operatorDesktopSizes";
import OperatorMapCanvas from "@/components/warehouse/OperatorMapCanvas";
import { WAVE_STATION_LOCATION_TYPES } from "@/api/warehouseMap";
import {
  useDirectOutboundFromInbound,
  useOldestIncompleteInbound,
  useInboundAssignedDetails,
  useAssignInboundToBuffer,
} from "@/hooks/useInbound";
import { useStationProductAggregate } from "@/hooks/useOutboundTask";
import { useSortingWaves } from "@/hooks/useSortingWave";
import {
  useLocationByCodeMap,
  useLocationsByZone,
} from "@/hooks/useWarehouseLocation";
import { useLocationDetail } from "@/hooks/useWarehouseMap";
import { useProduct } from "@/hooks/useProduct";
import { getInboundBufferAssignmentApi } from "@/api/inboundOperator";
import type { InboundBufferAssignment } from "@/types/inbound";
import type { StationProductLine } from "@/types/outboundTask";
import type { WarehouseLocation } from "@/types/warehouseLocation";
import { getApiErrorDetail } from "@/types/apiError";
import { toDisplayInteger } from "@/utils/number";
import { formatDisplayBin } from "@/utils/locationBin";
import type { SortingWave } from "@/types/sortingWave";

const EMPTY_SORTING_WAVES: SortingWave[] = [];

type DirectOutboundFromInboundBoardProps = {
  zoneId: number;
  onImportClick?: () => void;
  importLoading?: boolean;
  importDisabled?: boolean;
};

function locationLabel(loc: {
  id: number;
  location_code: string;
  bin?: string | null;
  location_type?: string | null;
  status?: string | null;
}) {
  const code =
    formatDisplayBin(loc.bin, loc.location_type) ||
    (loc.location_code || "").trim() ||
    `#${loc.id}`;
  const status = (loc.status || "").trim();
  return status ? `${code} · ${status}` : code;
}

function displayBin(loc: {
  bin?: string | null;
  location_type?: string | null;
  location_code?: string | null;
}): string {
  return (
    formatDisplayBin(loc.bin, loc.location_type) ||
    (loc.location_code || "").trim() ||
    ""
  ).toUpperCase();
}

/** Ô chọn được trên map: mã bin BP* (chia chọn) hoặc CX* (cửa xuất). */
function isBpOrCxBin(loc: {
  bin?: string | null;
  location_type?: string | null;
  location_code?: string | null;
}): boolean {
  const bin = displayBin(loc);
  return bin.startsWith("BP") || bin.startsWith("CX");
}

export default function DirectOutboundFromInboundBoard({
  zoneId = 1,
  onImportClick,
  importLoading,
  importDisabled,
}: DirectOutboundFromInboundBoardProps) {
  const { data: sortingWavesData } = useSortingWaves(zoneId);
  const sortingWaves = sortingWavesData ?? EMPTY_SORTING_WAVES;
  const waveIdsKey = useMemo(
    () => sortingWaves.map((wave) => wave.id).join(","),
    [sortingWaves],
  );
  const { data: incompleteInbound } = useOldestIncompleteInbound(zoneId);
  const orderId = incompleteInbound?.order?.id ?? 0;
  const { data: products = [] } = useProduct(zoneId);

  const { data: allLocations = [], isLoading: locationsLoading } =
    useLocationsByZone(zoneId);
  const { locationByCode } = useLocationByCodeMap(zoneId);
  const sendMutation = useDirectOutboundFromInbound();

  const [waveId, setWaveId] = useState<number | null>(null);
  const [inboundLocationId, setInboundLocationId] = useState<
    number | undefined
  >();
  const [outboundLocationId, setOutboundLocationId] = useState<
    number | undefined
  >();
  const [selectedProduct, setSelectedProduct] =
    useState<StationProductLine | null>(null);
  const [assignmentRefreshKey, setAssignmentRefreshKey] = useState(0);
  const [inboundAssignment, setInboundAssignment] =
    useState<InboundBufferAssignment | null>(null);

  const { data: assignedPayload } = useInboundAssignedDetails(orderId, orderId > 0);
  const assignedDetails = assignedPayload?.details ?? [];
  const assignMutation = useAssignInboundToBuffer();

  useEffect(() => {
    if (sortingWaves.length === 0) {
      setWaveId(null);
      return;
    }
    setWaveId((prev) => {
      if (prev != null && sortingWaves.some((w) => w.id === prev)) return prev;
      return sortingWaves[0].id;
    });
  }, [waveIdsKey, sortingWaves]);

  const inboundBuffers = useMemo(
    () =>
      allLocations.filter(
        (loc) => (loc.location_type || "").trim() === "inbound_buffer",
      ),
    [allLocations],
  );

  /** Toàn bộ station của mọi wave — để hiện đủ 2 khu chia chọn. */
  const allWaveStationIds = useMemo(() => {
    const ids: number[] = [];
    for (const wave of sortingWaves) {
      ids.push(...(wave.sorting_stations ?? []));
      ids.push(...(wave.outbound_stations ?? []));
    }
    return [...new Set(ids)];
  }, [sortingWaves]);

  const outboundStations = useMemo(() => {
    return allLocations.filter(
      (loc) => (loc.location_type || "").trim() === "outbound_station",
    );
  }, [allLocations]);

  const inboundOptions = useMemo(
    () =>
      inboundBuffers.map((loc) => ({
        value: loc.id,
        label: locationLabel(loc),
      })),
    [inboundBuffers],
  );

  const outboundOptions = useMemo(
    () =>
      outboundStations.map((loc) => ({
        value: loc.id,
        label: locationLabel(loc),
      })),
    [outboundStations],
  );

  /** Trái: chỉ ô nhập BP/CX (fallback toàn bộ inbound_buffer nếu không có). */
  const inboundInteractiveCodes = useMemo(() => {
    const bpCx = inboundBuffers
      .filter(isBpOrCxBin)
      .map((loc) => loc.location_code);
    if (bpCx.length > 0) return bpCx;
    return inboundBuffers.map((loc) => loc.location_code);
  }, [inboundBuffers]);

  /** Phải: chỉ BP (chia chọn) + CX (cửa xuất). */
  const waveInteractiveCodes = useMemo(() => {
    const idSet =
      allWaveStationIds.length > 0 ? new Set(allWaveStationIds) : null;
    return allLocations
      .filter((loc) => {
        const t = (loc.location_type || "").trim();
        if (t !== "sorting_station" && t !== "outbound_station") return false;
        if (idSet && !idSet.has(loc.id)) return false;
        return isBpOrCxBin(loc);
      })
      .map((loc) => loc.location_code);
  }, [allLocations, allWaveStationIds]);

  useEffect(() => {
    if (!inboundLocationId) {
      setInboundAssignment(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const assignment =
          await getInboundBufferAssignmentApi(inboundLocationId);
        if (!cancelled) setInboundAssignment(assignment);
      } catch {
        if (!cancelled) setInboundAssignment(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [inboundLocationId, assignmentRefreshKey]);

  const assignedDetail = inboundAssignment?.details?.[0] ?? null;
  const inboundReady =
    Boolean(inboundAssignment?.is_assigned) && assignedDetail != null;

  const aggregateQuery = useStationProductAggregate(
    zoneId,
    waveId ?? 0,
    outboundLocationId ?? 0,
    { enabled: zoneId > 0 && waveId != null && outboundLocationId != null }
  );

  useEffect(() => {
    if (!outboundLocationId) return;
    const stationProducts = aggregateQuery.data?.products ?? [];
    if (stationProducts.length > 0) {
      const match = stationProducts.find((p) => p.product_id === assignedDetail?.product_id);
      setSelectedProduct(match || stationProducts[0]);
    } else {
      setSelectedProduct(null);
    }
  }, [aggregateQuery.data?.products, assignedDetail?.product_id, outboundLocationId]);

  const itemOutboundIds = useMemo(() => {
    if (!selectedProduct) return [] as number[];
    const ids = selectedProduct.by_customer.flatMap((c) => c.item_outbound_ids);
    return [...new Set(ids)];
  }, [selectedProduct]);

  const inboundLocationCode =
    inboundBuffers.find((l) => l.id === inboundLocationId)?.location_code ??
    null;
  const selectedInboundLocation =
    inboundBuffers.find((location) => location.id === inboundLocationId) ?? null;
  const isSelectedBypass =
    selectedInboundLocation != null &&
    displayBin(selectedInboundLocation).startsWith("BP");
  const { data: inboundLocationDetail } = useLocationDetail(
    isSelectedBypass ? inboundLocationId ?? undefined : undefined,
  );
  const productById = useMemo(
    () => new Map(products.map((product) => [product.id, product])),
    [products],
  );
  const bypassMetadata = useMemo(() => {
    const stocks = inboundLocationDetail?.item_stock ?? [];
    if (!isSelectedBypass || stocks.length === 0) {
      return "Chưa chọn ô bypass có hàng";
    }
    return stocks
      .map((stock) => {
        const product = productById.get(stock.item_id);
        const sku = stock.sku || product?.sku || `#${stock.item_id}`;
        const name = product?.name || "Chưa có tên hàng";
        const quantity = toDisplayInteger(Number(stock.quantity || 0));
        return `${sku} - ${name} - ${quantity}`;
      })
      .join("; ");
  }, [inboundLocationDetail?.item_stock, isSelectedBypass, productById]);
  const outboundLocationCode =
    outboundStations.find((l) => l.id === outboundLocationId)?.location_code ??
    null;

  const resolveWaveForLocation = (locationId: number) => {
    for (const wave of sortingWaves) {
      if ((wave.sorting_stations ?? []).includes(locationId)) return wave.id;
      if ((wave.outbound_stations ?? []).includes(locationId)) return wave.id;
    }
    return null;
  };

  /** Fill điểm nhập và gán SP tự động */
  const fillInbound = (locationId: number) => {
    setInboundLocationId(locationId);
    setSelectedProduct(null);
    if (orderId <= 0) {
      message.warning("Không có đơn nhập đang xử lý trong kho này");
      return;
    }

    // Tự động gán detail đầu tiên chưa gán
    const pendingDetail = assignedDetails.find((d) => d.status === "pending");
    if (pendingDetail) {
      assignMutation.mutate(
        {
          orderId,
          data: { location_id: locationId, detail_id: pendingDetail.detail_id },
        },
        {
          onSuccess: () => {
            message.success(`Đã tự động gán sản phẩm vào ô`);
            setAssignmentRefreshKey((k) => k + 1);
          },
        }
      );
    }
  };

  /** Fill điểm xuất (+ suy ra wave nếu cần) */
  const fillOutbound = (locationId: number) => {
    const owningWave = resolveWaveForLocation(locationId);
    if (owningWave != null) setWaveId(owningWave);
    setOutboundLocationId(locationId);
    setSelectedProduct(null);

    if (owningWave == null) {
      message.warning("Điểm xuất không thuộc vị trí sorting nào");
      return;
    }
  };

  const fillSortingWave = (locationId: number) => {
    const owningWave = resolveWaveForLocation(locationId);
    if (owningWave == null) return;
    setWaveId(owningWave);
  };

  const handleInboundMapClick = (payload: { locationCode: string }) => {
    const location = locationByCode[payload.locationCode];
    if (!location) {
      message.error(
        `Không tìm thấy warehouse location cho mã ${payload.locationCode}`,
      );
      return;
    }
    if ((location.location_type || "").trim() !== "inbound_buffer") {
      message.error("Điểm nhập phải là inbound_buffer.");
      return;
    }
    fillInbound(location.id);
  };


  const handleWaveMapClick = (payload: { locationCode: string }) => {
    const location = locationByCode[payload.locationCode] as
      | WarehouseLocation
      | undefined;
    if (!location) {
      message.error(
        `Không tìm thấy warehouse location cho mã ${payload.locationCode}`,
      );
      return;
    }
    if (!isBpOrCxBin(location)) {
      return;
    }
    const locType = (location.location_type || "").trim();
    if (locType === "sorting_station") {
      fillSortingWave(location.id);
      return;
    }
    if (locType === "outbound_station") {
      fillOutbound(location.id);
      return;
    }
  };



  const handleSendCommand = () => {
    const resolvedWaveId =
      waveId ??
      (outboundLocationId != null
        ? resolveWaveForLocation(outboundLocationId)
        : null);
    if (!inboundLocationId || !outboundLocationId || !resolvedWaveId) {
      message.warning("Vui lòng chọn đủ điểm nhập và điểm xuất");
      return;
    }
    if (waveId == null) setWaveId(resolvedWaveId);
    if (!assignedDetail || !inboundAssignment?.inbound_order_id) {
      message.warning(
        "Điểm nhập chưa được gán sản phẩm — bấm «Gán / hủy SP» để gán",
      );
      return;
    }
    if (!selectedProduct || itemOutboundIds.length === 0) {
      message.warning("Chưa chọn SKU xuất — bấm «Chọn SKU xuất»");
      return;
    }
    if (selectedProduct.product_id !== assignedDetail.product_id) {
      message.warning("SKU xuất phải khớp sản phẩm đã gán trên điểm nhập");
      return;
    }

    const inboundQty = Number(assignedDetail.expected_quantity || 0);
    const outboundNeed = Number(selectedProduct.total_quantity || 0);
    if (inboundQty <= 0) {
      message.warning("Số lượng inbound không hợp lệ");
      return;
    }
    if (outboundNeed <= 0) {
      message.warning("Nhu cầu outbound không hợp lệ");
      return;
    }

    const appliedQty = Math.min(inboundQty, outboundNeed);
    const surplusQty = Math.max(0, inboundQty - outboundNeed);
    const shortageQty = Math.max(0, outboundNeed - inboundQty);

    Modal.confirm({
      title: "Xác nhận xuất trực tiếp",
      width: OPERATOR_DESKTOP.modal.default,
      content: (
        <div className="space-y-2 text-sm text-slate-600">
          <p>
            Xuất hết{" "}
            <strong>
              {selectedProduct.product_sku || `#${selectedProduct.product_id}`}
            </strong>{" "}
            · SL inbound <strong>{toDisplayInteger(inboundQty)}</strong> →
            outbound station
          </p>
          <p>
            Trừ đơn xuất: <strong>{toDisplayInteger(appliedQty)}</strong>
            {shortageQty > 0
              ? ` (thiếu ${toDisplayInteger(shortageQty)} so với nhu cầu)`
              : null}
            {surplusQty > 0
              ? ` · thừa ${toDisplayInteger(surplusQty)} → tạo lệnh return`
              : null}
          </p>
        </div>
      ),
      okText: "Gửi lệnh",
      cancelText: "Hủy",
      onOk: () =>
        sendMutation.mutateAsync(
          {
            zone_id: zoneId,
            inbound_location_id: inboundLocationId,
            outbound_location_id: outboundLocationId,
            inbound_order_id: inboundAssignment.inbound_order_id!,
            inbound_detail_id: assignedDetail.detail_id,
            sorting_wave_id: resolvedWaveId,
            item_outbound_ids: itemOutboundIds,
            quantity: inboundQty,
          },
          {
            onSuccess: (result) => {
              const surplus = Number(result.surplus_quantity || 0);
              message.success(
                surplus > 0
                  ? `Đã xuất ${toDisplayInteger(result.quantity)} · trừ đơn ${toDisplayInteger(result.applied_quantity)} · lệnh return #${result.return_task_id}`
                  : `Đã xuất trực tiếp ${toDisplayInteger(result.quantity)} · trừ đơn ${toDisplayInteger(result.applied_quantity)} · lệnh #${result.command_id}`,
              );
              setAssignmentRefreshKey((k) => k + 1);
              setSelectedProduct(null);
            },
            onError: (err) => {
              message.error(
                getApiErrorDetail(err, "Không thể gửi lệnh xuất trực tiếp"),
              );
            },
          },
        ),
    });
  };

  const canSend =
    inboundReady &&
    outboundLocationId != null &&
    selectedProduct != null &&
    itemOutboundIds.length > 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-panel">
      <div className="grid shrink-0 grid-cols-1 items-end gap-2 border-b border-stripe-hairline px-3 py-2.5 sm:px-4 md:grid-cols-3 xl:grid-cols-[repeat(3,minmax(0,1fr))_auto]">
        <div className="min-w-0 space-y-1">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
            Điểm nhập
          </label>
          <div className="flex gap-2">
            <Select
              showSearch
              optionFilterProp="label"
              loading={locationsLoading}
              value={inboundLocationId}
              placeholder="Chọn / click map trái"
              onChange={(next) => fillInbound(Number(next))}
              options={inboundOptions}
              disabled={zoneId <= 0 || locationsLoading}
              className="!h-12 flex-1 min-w-0 [&_.ant-select-selection-item]:!text-base [&_.ant-select-selection-item]:!leading-[46px] [&_.ant-select-selection-placeholder]:!text-base [&_.ant-select-selection-placeholder]:!leading-[46px] [&_.ant-select-selector]:!h-12"
              notFoundContent="Không có inbound_buffer"
            />
          </div>
        </div>

        <div className="min-w-0 space-y-1">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
            Điểm xuất
          </label>
          <div className="flex gap-2">
            <Select
              showSearch
              optionFilterProp="label"
              loading={locationsLoading}
              value={outboundLocationId}
              placeholder="Chọn / click CX trên map"
              onChange={(next) => fillOutbound(Number(next))}
              options={outboundOptions}
              disabled={zoneId <= 0 || locationsLoading}
              className="!h-12 flex-1 min-w-0 [&_.ant-select-selection-item]:!text-base [&_.ant-select-selection-item]:!leading-[46px] [&_.ant-select-selection-placeholder]:!text-base [&_.ant-select-selection-placeholder]:!leading-[46px] [&_.ant-select-selector]:!h-12"
              notFoundContent="Không có outbound_station"
            />
          </div>
        </div>
        <div className="min-w-0 space-y-1">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500">
            Metadata
          </label>
          <Input
            readOnly
            value={bypassMetadata}
            title={bypassMetadata}
            className="!h-12 !w-full !truncate !border-cyan-300/40 !bg-cyan-50/50 !px-3 !font-mono !text-base !font-semibold !text-slate-700"
          />
        </div>
        <Button
          variant="primary"
          icon={<RobotOutlined />}
          onClick={handleSendCommand}
          disabled={!canSend}
          loading={sendMutation.isPending}
          className="!h-12 !text-sm"
        >
          Gửi lệnh
        </Button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden xl:grid-cols-2">
        <div className="flex min-h-0 min-w-0 flex-col overflow-hidden xl:border-r xl:border-stripe-hairline">
          <div className="flex shrink-0 items-center border-b border-stripe-hairline px-3 py-2">
            <h4 className="text-sm font-semibold text-brand-dark">
              Sơ đồ điểm nhập
            </h4>
          </div>
          <div className="relative min-h-0 flex-1 overflow-hidden bg-industrial-pattern p-2">
            {zoneId > 0 ? (
              <OperatorMapCanvas
                zoneId={[10, 16]}
                showInboundSeparator={true}
                tuning={OPERATOR_DIRECT_OUTBOUND_MAP_TUNING}
                selectedCodes={inboundLocationCode ? [inboundLocationCode] : undefined}
                interactiveCodes={inboundInteractiveCodes}
                onBufferCellClick={handleInboundMapClick}
                className="!h-full"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">
                Chọn kho để xem sơ đồ điểm nhập
              </div>
            )}
          </div>
        </div>

        <div className="flex min-h-0 min-w-0 flex-col overflow-hidden border-t border-stripe-hairline xl:border-t-0">
          <div className="flex shrink-0 items-center border-b border-stripe-hairline px-3 py-2">
            <h4 className="text-sm font-semibold text-brand-dark">
              Sơ đồ chia chọn & cửa xuất
            </h4>
          </div>
          <div className="relative min-h-0 flex-1 overflow-hidden bg-industrial-pattern p-2">
            {zoneId > 0 ? (
              <OperatorMapCanvas
                key={`wave-all-${allWaveStationIds.join(",") || "zone"}`}
                zoneId={[12, 13]}
                tuning={OPERATOR_DIRECT_OUTBOUND_MAP_TUNING}
                selectedCodes={outboundLocationCode ? [outboundLocationCode] : undefined}
                interactiveCodes={waveInteractiveCodes}
                onBufferCellClick={handleWaveMapClick}
                className="!h-full"
              />
            ) : (
              <div className="flex h-full items-center justify-center px-4 text-center text-sm text-slate-500">
                Chọn kho để xem sơ đồ chia chọn
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
