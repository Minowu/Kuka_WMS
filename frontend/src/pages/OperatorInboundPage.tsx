import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import type { ColumnsType } from "antd/es/table";
import {
  ContainerOutlined,
  ExportOutlined,
  FileExcelOutlined,
  RobotOutlined,
  ScanOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import {
  Button,
  Modal,
  Space,
  Table,
  cn,
  message,
} from "@/components/ui";
import { Spin } from "antd";
import { useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import {
  OPERATOR_DESKTOP,
  OPERATOR_INBOUND_MAP_TUNING,
  operatorDesktopClass,
  operatorDesktopTableWidths,
} from "@/constants/operatorDesktopSizes";
import AssignInboundBufferModal from "@/components/inbound/AssignInboundBufferModal";
import UnassignInboundBufferModal from "@/components/inbound/UnassignInboundBufferModal";
import OperatorMapCanvas, {
  type BufferCellClickPayload,
} from "@/components/warehouse/OperatorMapCanvas";
import OperatorInboundOrderBrowser from "@/components/inbound/OperatorInboundOrderBrowser";
import DirectOutboundFromInboundBoard from "@/components/inbound/DirectOutboundFromInboundBoard";
import InboundLocationInfoModal from "@/components/inbound/InboundLocationInfoModal";
import { exportInboundOrderMasanApi } from "@/api/masan";
import { useCallerMasanInbound } from "@/hooks/useMasanInbound";
import { useZonesMapStatus } from "@/hooks/useWarehouseMap";

import { useAppStore } from "@/store/useAppStore";

import {
  getInboundBufferAssignmentApi,
  getInboundDailyReportApi,
  parseMasanInboundExcelApi,
  suggestMasanAllocationApi,
  createMasanInboundOrderApi,
} from "@/api/inboundOperator";
import {
  useInboundAssignedDetails,
  useInboundList,
  useOldestIncompleteInbound,
} from "@/hooks/useInbound";
import { useLocationByCodeMap } from "@/hooks/useWarehouseLocation";
import type {
  InboundAssignedDetail,
  InboundBufferAssignment,
  MasanCreatePayload,
} from "@/types/inbound";
import { getApiErrorDetail } from "@/types/apiError";
import { SOURCE_TABS, type SourceTabKey } from "@/data/mockOperatorInbound";
import { toDisplayInteger } from "@/utils/number";

type SideListTab = "orders" | "commands";

const INBOUND_MAP_ZONE_IDS = [2, 3];

function formatAssignedSkuLot(row: InboundAssignedDetail): string {
  const sku = row.product_sku?.trim() || "—";
  const lot = row.lot_number?.trim();
  return lot ? `${sku} / ${lot}` : sku;
}

const ASSIGNED_STATUS_LABEL: Record<string, string> = {
  partial: "Đã gán",
  pending: "Chưa gán",
  completed: "Hoàn tất",
};

const EMPTY_ASSIGNED_DETAILS: InboundAssignedDetail[] = [];

const SOURCE_TAB_META: Record<
  SourceTabKey,
  { icon: typeof ContainerOutlined; activeBadge: string }
> = {
  cont: {
    icon: ContainerOutlined,
    activeBadge: "bg-brand-primary/15 text-brand-primary",
  },
  direct: {
    icon: ExportOutlined,
    activeBadge: "bg-warning-100 text-warning-700",
  },
};

export default function OperatorInboundPage() {
  const warehouseId = useAppStore((s) => s.selectedWarehouseId);

  const { data } = useOldestIncompleteInbound(warehouseId);
  const orderId = data?.order?.id ?? 0;
  const { data: assignedPayload, isLoading: assignedLoading } =
    useInboundAssignedDetails(orderId, orderId > 0);
  const assignedDetails = assignedPayload?.details ?? EMPTY_ASSIGNED_DETAILS;
  const { data: inboundOrders = [],
    isLoading: inboundOrdersLoading,
    isError: inboundOrdersError,
  } = useInboundList(warehouseId);
  const { locationByCode } = useLocationByCodeMap(warehouseId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mapSingleClickTimerRef = useRef<number | null>(null);

  const [sourceTab, setSourceTab] = useState<SourceTabKey>("cont");
  const [sideListTab, setSideListTab] = useState<SideListTab>("orders");
  const [mode, setMode] = useState<"auto" | "manual">("auto");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [unassignModalOpen, setUnassignModalOpen] = useState(false);
  const [bufferAssignment, setBufferAssignment] =
    useState<InboundBufferAssignment | null>(null);
  const [selectedBufferCode, setSelectedBufferCode] = useState<string | null>(
    null,
  );
  const [selectedBufferLocationId, setSelectedBufferLocationId] = useState<
    number | null
  >(null);
  const [selectedAutoColumnCodes, setSelectedAutoColumnCodes] = useState<
    string[]
  >([]);
  const [locationInfoOpen, setLocationInfoOpen] = useState(false);
  const [infoLocationId, setInfoLocationId] = useState<number | null>(null);

  const [isMasanImporting, setIsMasanImporting] = useState(false);
  const [isMasanPreviewOpen, setIsMasanPreviewOpen] = useState(false);
  const [masanDraftPayload, setMasanDraftPayload] = useState<MasanCreatePayload | null>(null);
  const [masanPreviewData, setMasanPreviewData] = useState<any[]>([]);

  const [isExportingDailyExcel, setIsExportingDailyExcel] = useState(false);
  const [isExportingDetailReport, setIsExportingDetailReport] = useState(false);
  const [focusedInboundOrderId, setFocusedInboundOrderId] = useState<
    number | null
  >(null);

  const callerMutation = useCallerMasanInbound();
  const queryClient = useQueryClient();
  const inboundMapStatus = useZonesMapStatus(INBOUND_MAP_ZONE_IDS);
  const inboundLocationIdByCode = useMemo(() => {
    const map = new Map<string, number>();
    for (const cell of inboundMapStatus.items) {
      map.set(cell.location_code, cell.id);
    }
    return map;
  }, [inboundMapStatus.items]);
  const callerLocationIds = useMemo(() => {
    const codes =
      selectedAutoColumnCodes.length > 0
        ? selectedAutoColumnCodes
        : [...inboundLocationIdByCode.keys()];
    const ids = codes
      .map((code) => inboundLocationIdByCode.get(code))
      .filter((id): id is number => id != null);
    return [...new Set(ids)];
  }, [inboundLocationIdByCode, selectedAutoColumnCodes]);

  /** Sơ đồ operator vẽ zone 2+3; tra cứu id theo status map đó, không theo warehouseId. */
  const resolveInboundMapLocationId = (locationCode: string): number | null => {
    const fromInboundMap = inboundLocationIdByCode.get(locationCode);
    if (fromInboundMap != null) return fromInboundMap;
    return locationByCode[locationCode]?.id ?? null;
  };

  const resetImportState = () => {
    setMasanDraftPayload(null);
    setMasanPreviewData([]);
  };

  const closeImportPreview = () => {
    setIsMasanPreviewOpen(false);
    resetImportState();
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleImportFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (warehouseId <= 0) {
      message.error("Vui lòng chọn kho trước khi import");
      return;
    }

    setIsMasanImporting(true);
    resetImportState();

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('warehouse_id', warehouseId.toString());
      console.log("cont test", warehouseId)
      formData.append('inbound_type', 'auto');

      const parseResult = await parseMasanInboundExcelApi(formData);

      const errors = parseResult.preview_rows.filter((r: any) => r.error !== null);
      if (errors.length > 0) {
        Modal.error({
          title: "Lỗi file Excel",
          width: OPERATOR_DESKTOP.modal.sm,
          destroyOnHidden: true,
          content: (
            <ul className={`mt-2 ${operatorDesktopClass.listMax64} list-disc space-y-1 overflow-y-auto pl-5 text-sm`}>
              {errors.map((err: any, index: number) => (
                <li key={index}>
                  Dòng {err.row_no}: {err.error}
                </li>
              ))}
            </ul>
          ),
        });
        return;
      }

      if (!parseResult.suggest_allocation || parseResult.suggest_allocation.line_items.length === 0) {
        message.error("Không có dòng dữ liệu hợp lệ để tạo đơn.");
        return;
      }

      const suggestResult = await suggestMasanAllocationApi(parseResult.suggest_allocation);

      const orderCode = `IN-${dayjs().format("YYYYMMDD-HHmmss")}`;
      const createPayload: MasanCreatePayload = {
        order_code: orderCode,
        note: "Import Masan",
        warehouse_id: warehouseId,
        details: {
          source: "masan_import",
          total_rows: parseResult.total_rows,
          valid_rows: parseResult.valid_rows,
          invalid_rows: parseResult.invalid_rows
        },
        line_items: parseResult.suggest_allocation.line_items.map((line, i) => {
          const suggestedLine = suggestResult.line_items[i];
          return {
            from_location_id: line.details.from_location_id,
            to_location_id: suggestedLine.target_location_id,
            details: line.details,
            allocations: suggestedLine.line_items,
            _preview_sku: line.details.sku,
            _preview_vehicle: line.details.vehicle_no,
            _preview_to_location_name: suggestedLine.target_location_name,
            _preview_quantity: suggestedLine.line_items.reduce((sum, item) => sum + item.quantity, 0)
          };
        })
      };

      setMasanDraftPayload(createPayload);
      setMasanPreviewData(createPayload.line_items);
      setIsMasanPreviewOpen(true);
    } catch (err: unknown) {
      message.error(getApiErrorDetail(err, "Không thể đọc hoặc phân bổ vị trí từ file Excel"));
    } finally {
      setIsMasanImporting(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!masanDraftPayload) return;

    setIsMasanImporting(true);
    try {
      await createMasanInboundOrderApi(masanDraftPayload, "auto");
      message.success("Import đơn nhập Masan thành công!");
      setIsMasanPreviewOpen(false);
      resetImportState();
      queryClient.invalidateQueries({ queryKey: ["inbound-orders"] });
      queryClient.invalidateQueries({ queryKey: ["inbound", "oldest-incomplete"] });
    } catch (err: unknown) {
      message.error(getApiErrorDetail(err, "Không thể tạo đơn nhập từ file Excel"));
    } finally {
      setIsMasanImporting(false);
    }
  };

  const handleExportDailyExcel = async () => {
    if (warehouseId <= 0) {
      message.warning("Vui lòng chọn kho trước khi xuất");
      return;
    }

    setIsExportingDailyExcel(true);
    try {
      const report = await getInboundDailyReportApi(warehouseId);
      if (report.lines.length === 0) {
        message.warning("Không có đơn nhập nào được tạo hôm nay để xuất");
        return;
      }
      const { downloadInboundDailyReportExcel } =
        await import("@/utils/inboundDetailExport");
      downloadInboundDailyReportExcel(report);
      message.success(
        `Đã xuất báo cáo nhập theo ngày (${report.lines.length} dòng)`,
      );
    } catch (err: unknown) {
      message.error(getApiErrorDetail(err, "Không thể xuất báo cáo Excel"));
    } finally {
      setIsExportingDailyExcel(false);
    }
  };

  const handleExportDetailReport = async () => {
    const exportOrderId =
      focusedInboundOrderId ?? inboundOrders[0]?.id ?? null;
    if (exportOrderId == null) {
      message.warning("Không có đơn nhập nào để xuất báo cáo");
      return;
    }

    setIsExportingDetailReport(true);
    try {
      message.loading({ content: "Đang xuất Excel...", key: "masan-inbound-export" });
      await exportInboundOrderMasanApi(exportOrderId);
      const orderCode =
        inboundOrders.find((o) => o.id === exportOrderId)?.order_code ??
        String(exportOrderId);
      message.success({
        content: `Đã tải báo cáo nhập Masan (${orderCode})`,
        key: "masan-inbound-export",
      });
    } catch (err: unknown) {
      message.error({
        content: getApiErrorDetail(err, "Không thể xuất báo cáo Excel"),
        key: "masan-inbound-export",
      });
    } finally {
      setIsExportingDetailReport(false);
    }
  };

  useEffect(
    () => () => {
      if (mapSingleClickTimerRef.current != null) {
        window.clearTimeout(mapSingleClickTimerRef.current);
      }
    },
    [],
  );

  useEffect(() => {
    const nextIds = assignedDetails.map((d) => d.detail_id);
    setSelectedIds((prev) => {
      if (
        nextIds.length === prev.length &&
        nextIds.every((id, index) => id === prev[index])
      ) {
        return prev;
      }
      return nextIds;
    });
  }, [assignedDetails]);

  const handleManualBufferDoubleClick = async (
    payload: BufferCellClickPayload,
  ) => {
    if (!data?.order?.id) {
      message.warning("Không có đơn nhập đang xử lý trong kho này.");
      return;
    }
    const locationId = resolveInboundMapLocationId(payload.locationCode);
    if (locationId == null) {
      message.error(
        `Không tìm thấy warehouse location cho mã ${payload.locationCode}`,
      );
      return;
    }
    setSelectedBufferCode(payload.locationCode);
    setSelectedBufferLocationId(locationId);

    try {
      const assignment = await getInboundBufferAssignmentApi(locationId);
      if (assignment.is_assigned) {
        setBufferAssignment(assignment);
        setUnassignModalOpen(true);
        setAssignModalOpen(false);
        return;
      }
      setBufferAssignment(null);
      setUnassignModalOpen(false);
      setAssignModalOpen(true);
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Không kiểm tra được trạng thái gán ô";
      message.error(detail);
    }
  };

  const openLocationInfo = (payload: BufferCellClickPayload) => {
    const locationId = resolveInboundMapLocationId(payload.locationCode);
    if (locationId == null) {
      message.error(
        `Không tìm thấy warehouse location cho mã ${payload.locationCode}`,
      );
      return;
    }
    setInfoLocationId(locationId);
    setLocationInfoOpen(true);
  };

  const handleBufferCellClick = (payload: BufferCellClickPayload) => {
    if (mapSingleClickTimerRef.current != null) {
      window.clearTimeout(mapSingleClickTimerRef.current);
    }
    // Chờ ngắn để phân biệt click đơn với double-click.
    mapSingleClickTimerRef.current = window.setTimeout(() => {
      mapSingleClickTimerRef.current = null;
      openLocationInfo(payload);
    }, 230);
  };

  const handleBufferCellDoubleClick = (payload: BufferCellClickPayload) => {
    if (mapSingleClickTimerRef.current != null) {
      window.clearTimeout(mapSingleClickTimerRef.current);
      mapSingleClickTimerRef.current = null;
    }

    if (mode === "manual") {
      setSelectedAutoColumnCodes([]);
      void handleManualBufferDoubleClick(payload);
      return;
    }

    const columnCodes = payload.columnLocationCodes?.length
      ? payload.columnLocationCodes
      : [payload.locationCode];
    setSelectedAutoColumnCodes(columnCodes);
    setSelectedBufferCode(null);
    setSelectedBufferLocationId(null);

    const normalize = (value: string | null | undefined) =>
      (value || "").trim().toUpperCase();
    const selectedLocationKeys = new Set<string>();
    for (const code of columnCodes) {
      selectedLocationKeys.add(normalize(code));
      const legacy = locationByCode[code];
      if (legacy) {
        selectedLocationKeys.add(normalize(legacy.location_code));
        selectedLocationKeys.add(normalize(legacy.bin));
      }
    }
    selectedLocationKeys.delete("");

    const matchingDetailIds = assignedDetails
      .filter((detail) =>
        [
          detail.location_code,
          detail.location_bin,
          detail.pickup_node_code,
        ].some((value) => selectedLocationKeys.has(normalize(value))),
      )
      .map((detail) => detail.detail_id);
    setSelectedIds(matchingDetailIds);

    message.info(
      `Đã chọn cột ${columnCodes.length} ô · bấm "Gọi robot nhập" để gọi cột này`,
    );
  };

  const clearBufferSelection = () => {
    setAssignModalOpen(false);
    setUnassignModalOpen(false);
    setBufferAssignment(null);
    setSelectedBufferCode(null);
    setSelectedBufferLocationId(null);
  };

  const handleCallRobot = () => {
    if (callerLocationIds.length === 0) {
      message.warning("Không có ô buffer nhập nào để gọi robot.");
      return;
    }

    const locationIds = [...callerLocationIds];
    const scopeLabel =
      selectedAutoColumnCodes.length > 0
        ? `cột đã chọn (${locationIds.length} ô)`
        : `tất cả ${locationIds.length} ô buffer nhập`;

    Modal.confirm({
      title: "Xác nhận gọi robot nhập",
      width: OPERATOR_DESKTOP.modal.default,
      content: (
        <div className="mt-2 space-y-1 text-sm text-slate-600">
          <p>
            Gọi robot cho <strong>{scopeLabel}</strong>.
          </p>
          <p>
            Mỗi ô sẽ lấy dòng nhập đang chờ (Khởi tạo) cũ nhất; ô không có
            dòng chờ sẽ được bỏ qua.
          </p>
        </div>
      ),
      okText: "Gọi robot",
      cancelText: "Hủy",
      onOk: () =>
        callerMutation.mutateAsync(locationIds, {
          onSuccess: (result) => {
            if (result.queued > 0) {
              message.success(`Đã gửi ${result.queued} lệnh xuống robot.`);
            } else {
              message.warning("Không có dòng nào đang chờ ở các ô đã chọn.");
            }
          },
          onError: (err) => {
            message.error(getApiErrorDetail(err, "Không thể gọi robot nhập"));
          },
        }),
    });
  };

  const assignedTw = operatorDesktopTableWidths.inboundAssignedDetails;
  const detailColumns: ColumnsType<InboundAssignedDetail> = [
    {
      title: "Biển số",
      dataIndex: "vehicle_number",
      ellipsis: true,
      render: (value: string | null) => (
        <span className="font-mono text-base font-semibold text-brand-dark">
          {value?.trim() || "—"}
        </span>
      ),
    },
    {
      title: "Vị trí",
      key: "location",
      width: 100,
      render: (_: unknown, record) => (
        <span className="font-mono text-base font-bold text-brand-dark">
          {record.location_bin?.trim() ||
            record.location_code?.trim() ||
            record.pickup_node_code?.trim() ||
            "—"}
        </span>
      ),
    },
    {
      title: "Mã hàng/LOT",
      key: "skuLot",
      ellipsis: true,
      render: (_: unknown, record) => (
        <span className="text-base font-medium text-brand-dark">
          {formatAssignedSkuLot(record)}
        </span>
      ),
    },
    {
      title: "SL",
      dataIndex: "expected_quantity",
      width: assignedTw.qty,
      align: "right",
      render: (qty: number) => (
        <span className="text-base font-semibold tabular-nums text-success-600">
          {toDisplayInteger(qty)}
        </span>
      ),
    },
    {
      title: "TT",
      dataIndex: "status",
      width: assignedTw.status,
      render: (status: string) => (
        <span className="inline-flex whitespace-nowrap rounded-full bg-warning-100 px-2 py-0.5 text-xs font-semibold text-warning-700">
          {ASSIGNED_STATUS_LABEL[status] ?? status}
        </span>
      ),
    },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">


      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-stripe-hairline bg-panel shadow-stripe-1">
        <div className="flex shrink-0 flex-nowrap items-stretch justify-between gap-0 overflow-hidden border-b border-stripe-hairline bg-panel-soft">
          <div className="flex min-w-0 flex-1 items-stretch gap-0 overflow-x-auto overflow-y-hidden">
            {SOURCE_TABS.map((tab) => {
              const isActive = sourceTab === tab.key;
              const Icon = SOURCE_TAB_META[tab.key].icon;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setSourceTab(tab.key)}
                  className={cn(
                    "relative flex min-h-12 min-w-[150px] items-center justify-center gap-2 px-4 py-2.5 text-xl font-bold transition-all",
                    isActive
                      ? "z-10 -mb-px border border-stripe-hairline border-b-white bg-white text-brand-primary shadow-[0_1px_0_0_#fff]"
                      : "mb-0 border border-transparent bg-transparent text-stripe-ink-mute hover:bg-white/40 hover:text-brand-dark",
                  )}
                >
                  <Icon
                    className={cn(
                      "text-lg",
                      isActive ? "text-brand-primary" : "text-stripe-ink-mute",
                    )}
                  />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="flex shrink-0 items-center gap-2 px-3 py-1.5">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={handleImportFileChange}
            />
            <div className="flex rounded-full border border-stripe-hairline bg-panel-soft p-1">
              <button
                type="button"
                onClick={() => {
                  setMode("auto");
                  setSelectedAutoColumnCodes([]);
                  setSelectedIds(
                    assignedDetails.map((detail) => detail.detail_id),
                  );
                  clearBufferSelection();
                }}
                className={cn(
                  "rounded-full px-4 py-1.5 text-base font-bold transition-all",
                  mode === "auto"
                    ? "bg-brand-primary text-white shadow-sm"
                    : "text-stripe-ink-mute hover:text-brand-dark hover:bg-white/50",
                )}
              >
                Tự động
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("manual");
                  setSelectedAutoColumnCodes([]);
                  setSelectedIds(
                    assignedDetails.map((detail) => detail.detail_id),
                  );
                  clearBufferSelection();
                }}
                className={cn(
                  "rounded-full px-4 py-1.5 text-base font-bold transition-all",
                  mode === "manual"
                    ? "bg-brand-primary text-white shadow-sm"
                    : "text-stripe-ink-mute hover:text-brand-dark hover:bg-white/50",
                )}
              >
                Thủ công (Manual)
              </button>
            </div>
          </div>
        </div>

        {sourceTab === "direct" ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <DirectOutboundFromInboundBoard
              zoneId={warehouseId}
              onImportClick={handleImportClick}
              importLoading={isMasanImporting}
              importDisabled={warehouseId <= 0}
            />
          </div>
        ) : (
          <div className="grid min-h-0 flex-1 grid-cols-1 items-stretch xl:grid-cols-5">
            <div className="flex min-h-0 flex-col overflow-hidden xl:col-span-3">
              <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-stripe-hairline px-4 py-2">
                <h3 className="text-4xl font-black text-brand-dark">
                  Sơ đồ nhập hàng
                </h3>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="primary"
                    icon={<ScanOutlined />}
                    onClick={() => console.log("[OperatorInbound] Quét QR gán ô")}
                    disabled={warehouseId <= 0}
                    className="!h-10 !px-4 !text-base !bg-cyan-600 hover:!bg-cyan-700 !border-cyan-600 hover:!border-cyan-700"
                  >
                    Quét QR gán ô
                  </Button>
                  <Button
                    variant="primary"
                    icon={<UploadOutlined />}
                    onClick={handleImportClick}
                    loading={isMasanImporting}
                    disabled={warehouseId <= 0}
                    className="!h-10 !px-4 !text-base"
                  >
                    Nhập dữ liệu đơn
                  </Button>
                  <Button
                    variant="secondary"
                    icon={<FileExcelOutlined />}
                    onClick={() => void handleExportDailyExcel()}
                    loading={isExportingDailyExcel}
                    disabled={warehouseId <= 0}
                    className="!h-10 !px-4 !text-base"
                  >
                    Xuất Excel nhập hàng
                  </Button>
                </div>
              </div>
              <div
                className={`relative flex ${operatorDesktopClass.boardFill} flex-col bg-industrial-pattern`}
              >
                <div className="relative min-h-0 flex-1 overflow-hidden rounded-lg bg-panel">
                  <OperatorMapCanvas
                    zoneId={[10, 16]}
                    showInboundSeparator={true}
                    className="!h-full"
                    tuning={OPERATOR_INBOUND_MAP_TUNING}
                    selectedCodes={
                      mode === "manual" && selectedBufferCode ? [selectedBufferCode] :
                        mode === "auto" ? selectedAutoColumnCodes : undefined
                    }
                    onBufferCellClick={handleBufferCellClick}
                    onBufferCellDoubleClick={handleBufferCellDoubleClick}
                  />
                </div>
              </div>
            </div>

            <div className="flex min-h-0 flex-col overflow-hidden border-t border-stripe-hairline xl:col-span-2 xl:border-l xl:border-t-0">
              <div className="flex shrink-0 items-stretch gap-0 overflow-x-auto border-b border-stripe-hairline bg-panel-soft">
                {(
                  [
                    {
                      key: "orders" as const,
                      label: "Lệnh nhập",
                      count: inboundOrders.length,
                    },
                    {
                      key: "commands" as const,
                      label: "Lệnh gọi",
                      count: assignedDetails.length,
                    },
                  ] as const
                ).map((tab) => {
                  const active = sideListTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setSideListTab(tab.key)}
                      className={cn(
                        "relative flex min-h-12 min-w-[150px] items-center justify-center gap-2 px-4 py-2.5 font-bold transition-all",
                        active
                          ? "z-10 -mb-px border border-stripe-hairline border-b-white bg-white text-brand-primary shadow-[0_1px_0_0_#fff]"
                          : "border border-transparent text-stripe-ink-mute hover:bg-white/50 hover:text-brand-dark",
                      )}
                    >
                      <span className="truncate text-2xl">{tab.label}</span>
                      <span
                        className={cn(
                          "rounded-full px-1.5 py-0.5 text-[11px] font-bold tabular-nums",
                          active
                            ? "bg-brand-primary/15 text-brand-primary"
                            : "bg-slate-200/80 text-slate-500",
                        )}
                      >
                        {tab.count}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="min-h-0 flex-1 overflow-hidden bg-panel">
                {sideListTab === "orders" ? (
                  <OperatorInboundOrderBrowser
                    key={warehouseId}
                    warehouseId={warehouseId}
                    orders={inboundOrders}
                    loading={inboundOrdersLoading}
                    error={inboundOrdersError}
                    onFocusedOrderIdChange={setFocusedInboundOrderId}
                  />
                ) : (
                  <Table<InboundAssignedDetail>
                    rowKey="detail_id"
                    size="middle"
                    pagination={false}
                    loading={assignedLoading}
                    columns={detailColumns}
                    dataSource={assignedDetails}
                    tableLayout="fixed"
                    locale={{
                      emptyText: orderId
                        ? "Chưa có lệnh nào được gán buffer"
                        : "Không có đơn nhập đang xử lý",
                    }}
                    rowSelection={{
                      selectedRowKeys: selectedIds,
                      onChange: (keys) => setSelectedIds(keys as number[]),
                      columnWidth: 40,
                    }}
                    className="h-full min-w-0"
                  />
                )}
              </div>

              <div className="grid shrink-0 grid-cols-2 gap-2 border-t border-stripe-hairline p-3">
                <Button
                  variant="secondary"
                  icon={<FileExcelOutlined />}
                  loading={isExportingDetailReport}
                  disabled={inboundOrders.length === 0}
                  onClick={() => void handleExportDetailReport()}
                  className="!h-10 !w-full justify-center !text-sm disabled:!border-stripe-hairline disabled:!bg-white disabled:!text-slate-400 disabled:!opacity-100"
                >
                  Xuất báo cáo
                </Button>
                <Button
                  variant="primary"
                  icon={<RobotOutlined />}
                  disabled={callerLocationIds.length === 0}
                  loading={callerMutation.isPending}
                  onClick={handleCallRobot}
                  className="!h-10 !w-full justify-center !text-sm disabled:!bg-brand-primary/45 disabled:!text-white disabled:!opacity-100"
                >
                  Gọi robot nhập
                  {selectedAutoColumnCodes.length > 0
                    ? ` (cột ${callerLocationIds.length} ô)`
                    : " (tất cả)"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      <InboundLocationInfoModal
        open={locationInfoOpen}
        zoneId={warehouseId}
        locationId={infoLocationId}
        onClose={() => {
          setLocationInfoOpen(false);
          setInfoLocationId(null);
        }}
      />

      {data?.order?.id && selectedBufferLocationId && selectedBufferCode ? (
        <AssignInboundBufferModal
          open={assignModalOpen}
          orderId={data.order.id}
          locationId={selectedBufferLocationId}
          locationCode={selectedBufferCode}
          onClose={clearBufferSelection}
        />
      ) : null}

      <UnassignInboundBufferModal
        open={unassignModalOpen}
        assignment={bufferAssignment}
        onClose={clearBufferSelection}
      />

      <Modal
        open={isMasanPreviewOpen}
        onCancel={closeImportPreview}
        width={OPERATOR_DESKTOP.modal.importInbound.width}
        destroyOnHidden
        title={
          <span className="text-brand-dark font-semibold">
            Xem trước import Masan
          </span>
        }
        footer={
          <Space>
            <Button variant="secondary" onClick={closeImportPreview}>
              Hủy
            </Button>
            <Button
              variant="primary"
              loading={isMasanImporting}
              disabled={isMasanImporting}
              onClick={() => void handleConfirmImport()}
            >
              {`Xác nhận tạo đơn (${masanPreviewData.length} dòng)`}
            </Button>
          </Space>
        }
      >
        <p className="mb-3 text-sm text-gray-500">
          Hệ thống đã tự động gợi ý vị trí cất. Vui lòng kiểm tra lại trước khi xác nhận tạo đơn.
        </p>

        <Table
          rowKey={(_, index) => String(index)}
          dataSource={masanPreviewData}
          pagination={false}
          scroll={{ x: 800, y: 400 }}
          className="[&_.ant-table-tbody_td]:align-top"
          size="small"
          columns={[
            {
              title: "SKU",
              dataIndex: "_preview_sku",
              key: "sku",
            },
            {
              title: "Số xe",
              dataIndex: "_preview_vehicle",
              key: "vehicle",
            },
            {
              title: "Vị trí gợi ý",
              dataIndex: "_preview_to_location_name",
              key: "location",
              render: (val) => <span className="font-bold text-brand-primary">{val}</span>
            },
            {
              title: "Số lượng",
              dataIndex: "_preview_quantity",
              key: "qty",
            }
          ]}
        />
      </Modal>
      <Spin spinning={isMasanImporting} fullscreen />
    </div>
  );
}
