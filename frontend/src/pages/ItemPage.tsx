import { useEffect, useMemo, useRef, useState } from "react";
import {
  PlusOutlined,
  SearchOutlined,
  DownloadOutlined,
  UploadOutlined,
  MinusCircleOutlined,
  BranchesOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { Item, CreateItemInput, ItemImportJobStatus } from "@/types/item";
import {
  Card,
  Table,
  Button,
  Input,
  InputNumber,
  Modal,
  Form,
  Space,
  message,
  Select,
  cn,
} from "@/components/ui";
import { Progress } from "antd";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  useItems,
  useCreateItem,
  useItemAnalyze,
  useImportItems,
  useDownloadLastImportItemFile,
} from "@/hooks/useItem";
import { useAppStore } from "@/store/useAppStore";
import { useNavigate } from "react-router-dom";
import { useWarehouses } from "@/hooks/useWarehouse";
import { useUnits } from "@/hooks/useUnit";
import { brand } from "@/components/ui/theme/tokens";
import { formatQuantity, parseQuantity } from "@/utils/formatQuantity";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import dayjs from "dayjs";

const PAGE_SIZE = 20;
const ITEM_FETCH_LIMIT = 100;
const STOCK_CHART_CHUNK_SIZE = 20;
const STOCK_CHART_AXIS_TICK = {
  fontSize: 11,
  fill: "#64748b",
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
};
const STOCK_COLOR_OK = brand.primary;
const STOCK_COLOR_BAD = "#ef4444";
const STOCK_COLOR_MAX = "#6ec8c8";
const STOCK_COLOR_MIN = brand.primaryDeep;

type StockChartStatus = "ok" | "low";

type StockChartPoint = {
  name: string;
  fullName: string;
  quantity: number;
  status: StockChartStatus;
  quantityOk: number | null;
  quantityBad: number | null;
};

function getStockStatus(quantity: number): StockChartStatus {
  if (quantity <= 0) return "low";
  return "ok";
}

function stockStatusLabel(status: StockChartStatus) {
  if (status === "low") return "Hết hàng";
  return "Sẵn sàng";
}

function stockStatusColor(status: StockChartStatus) {
  return status === "ok" ? STOCK_COLOR_OK : STOCK_COLOR_BAD;
}

function attachSplitQuantity(
  rows: Omit<StockChartPoint, "quantityOk" | "quantityBad">[],
): StockChartPoint[] {
  return rows.map((row, index) => {
    const isBad = row.status !== "ok";
    const prevBad = index > 0 && rows[index - 1].status !== "ok";
    const nextBad =
      index < rows.length - 1 && rows[index + 1].status !== "ok";

    return {
      ...row,
      quantityOk: isBad ? null : row.quantity,
      quantityBad: isBad || prevBad || nextBad ? row.quantity : null,
    };
  });
}

function QuantityStatusDot(props: {
  cx?: number;
  cy?: number;
  payload?: StockChartPoint;
}) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  const isBad = payload.status !== "ok";
  const fill = stockStatusColor(payload.status);
  return (
    <g>
      {isBad ? (
        <circle
          cx={cx}
          cy={cy}
          r={7}
          fill="none"
          stroke={STOCK_COLOR_BAD}
          strokeWidth={1.5}
          opacity={0.45}
        />
      ) : null}
      <circle
        cx={cx}
        cy={cy}
        r={isBad ? 4.5 : 3.5}
        fill={fill}
        stroke="#fff"
        strokeWidth={2}
      />
    </g>
  );
}

function StockChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload?: StockChartPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;
  const qtyColor = stockStatusColor(row.status);

  return (
    <div
      className="min-w-[200px] rounded-lg px-3 py-2.5 text-sm shadow-lg"
      style={{ backgroundColor: brand.dark }}
    >
      <p className="font-mono text-xs tracking-wide text-white/70">{row.name}</p>
      <p className="mt-0.5 text-sm font-medium text-white">{row.fullName}</p>
      <span
        className="mt-2 inline-block rounded px-1.5 py-0.5 text-[11px] font-semibold"
        style={{
          backgroundColor: `${qtyColor}33`,
          color: qtyColor,
        }}
      >
        {stockStatusLabel(row.status)}
      </span>
      <div className="mt-2 space-y-1 font-mono text-xs text-white/85">
        <p>
          <span style={{ color: qtyColor }}>Tồn kho</span>
          {"  "}
          {formatQuantity(row.quantity)}
        </p>
      </div>
    </div>
  );
}

const STOCK_LEGEND_ITEMS = [
  { label: "Sẵn sàng (có tồn kho)", color: STOCK_COLOR_OK },
  { label: "Hết tồn kho", color: STOCK_COLOR_BAD },
] as const;

function StockChartLegend() {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {STOCK_LEGEND_ITEMS.map((item) => (
        <span
          key={item.label}
          className="inline-flex items-center gap-1.5 rounded-md border border-slate-200/80 bg-white/80 px-2 py-1 text-[11px] font-medium text-slate-600"
        >
          {"dashed" in item && item.dashed ? (
            <span
              className="inline-block w-3.5 border-t-2"
              style={{ borderColor: item.color, borderStyle: "dashed" }}
            />
          ) : (
            <span
              className="inline-block h-0.5 w-3.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
          )}
          {item.label}
        </span>
      ))}
    </div>
  );
}
const ITEM_IMPORT_ACCEPT = ".csv";
const ITEM_IMPORT_REQUIRED_COLUMNS = [
  "Item No",
  "Item Name",
  "UOM1",
  "UOM Conversion / Pallet",
];

const ITEM_PAGE_TABS = [
  { key: "products" as const, label: "Sản phẩm" },
  { key: "stock-chart" as const, label: "Đồ thị tồn kho" },
];

type ItemPageTab = (typeof ITEM_PAGE_TABS)[number]["key"];

type CreateItemFormValues = Omit<CreateItemInput, "details"> & {
  detailEntries?: { key: string; value: string }[];
};

function formatDate(date?: string | null) {
  if (!date) return "—";
  return dayjs(date).format("DD/MM/YYYY HH:mm");
}

function formatKpi(value?: number | string) {
  return formatQuantity(value);
}

function formatInventoryValue(value?: number | string) {
  const amount = parseQuantity(value);
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function ItemPage() {
  const { selectedWarehouseId } = useAppStore();
  const { data: warehouses = [] } = useWarehouses();
  const { data: units = [], isLoading: isUnitsLoading } = useUnits();
  const selectedWarehouseName =
    warehouses.find((z) => z.id === selectedWarehouseId)?.name ??
    warehouses.find((z) => z.id === selectedWarehouseId)?.code ??
    "Chưa chọn kho";
  const [searchInput, setSearchInput] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<ItemPageTab>("products");
  const navigate = useNavigate();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [form] = Form.useForm<CreateItemFormValues>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importJob, setImportJob] = useState<ItemImportJobStatus | null>(null);

  const handleSearch = () => {
    setSubmittedQuery(searchInput.trim());
    setPage(1);
  };

  const { data, isLoading: isItemsLoading } = useItems({
    warehouse_id: selectedWarehouseId,
    q: submittedQuery || undefined,
    page_size: ITEM_FETCH_LIMIT,
  });
  const itemList = data?.items ?? [];
  const createMutation = useCreateItem();
  const importMutation = useImportItems();
  const downloadImportFileMutation = useDownloadLastImportItemFile();
  const { data: analyze, isLoading: isAnalyzeLoading } =
    useItemAnalyze(selectedWarehouseId);

  const stockLineChartChunks = useMemo(() => {
    const baseRows = [...itemList]
      .sort((a, b) => a.sku.localeCompare(b.sku, undefined, { numeric: true }))
      .map((item) => {
        const quantity = Number(item.quantity ?? 0);
        return {
          name: item.sku,
          fullName: item.name,
          quantity,
          status: getStockStatus(quantity),
        };
      });
    const rows = attachSplitQuantity(baseRows);

    const chunks: { data: StockChartPoint[]; yMax: number }[] = [];
    for (let i = 0; i < rows.length; i += STOCK_CHART_CHUNK_SIZE) {
      const data = rows.slice(i, i + STOCK_CHART_CHUNK_SIZE);
      const yMax = Math.max(
        0,
        ...data.map((row) => row.quantity),
      );
      chunks.push({ data, yMax: yMax > 0 ? yMax : 100 });
    }
    return chunks;
  }, [itemList]);

  useEffect(() => {
    if (isCreateOpen) {
      form.resetFields();
    }
  }, [isCreateOpen, form]);

  const handleOpenCreate = () => {
    setIsCreateOpen(true);
  };

  const handleCloseCreate = () => {
    setIsCreateOpen(false);
  };

  const kpiCards = [
    {
      label: "Tổng sản phẩm",
      value: formatKpi(analyze?.total_items),
      color: "#3aa6a6",
    },
    {
      label: "Tổng số lượng",
      value: formatKpi(analyze?.total_quantity),
      color: "#0f3d46",
    },
    {
      label: "Giá trị tồn kho",
      value: formatInventoryValue(analyze?.total_inventory_value),
      color: "#0f3460",
    },
    {
      label: "Số lượng còn ít",
      value: formatKpi(analyze?.total_low_stock),
      color: "#6b7280",
    },
  ];

  const handleCreate = (values: CreateItemFormValues) => {
    const details = Object.fromEntries(
      (values.detailEntries ?? [])
        .map(({ key, value }) => [key.trim(), value.trim()] as const)
        .filter(([key]) => key.length > 0),
    );
    createMutation.mutate(
      {
        sku: values.sku.trim(),
        name: values.name.trim(),
        description: values.description?.trim() ?? "",
        base_unit: Number(values.base_unit),
        standard_quantity_per_cart: Number(values.standard_quantity_per_cart ?? 120),
        warehouse_id: selectedWarehouseId,
        details,
      },
      {
        onSuccess: () => {
          message.success("Thêm sản phẩm thành công!");
          handleCloseCreate();
          setPage(1);
        },
        onError: (err) => {
          message.error(getApiErrorMessage(err, "Không thể thêm sản phẩm"));
        },
      },
    );
  };

  const handleDownloadImportFile = () => {
    if (!selectedWarehouseId) {
      message.error("Vui lòng chọn kho trước khi tải file.");
      return;
    }
    downloadImportFileMutation.mutate(
      { warehouseId: selectedWarehouseId },
      {
        onSuccess: () => {
          message.success("Đã tải file CSV import gần nhất");
        },
        onError: (err) => {
          message.error(getApiErrorMessage(err, "Không thể tải file import"));
        },
      },
    );
  };

  const handleImportClick = () => {
    if (!selectedWarehouseId) {
      message.error("Vui lòng chọn kho trước khi import.");
      return;
    }
    fileInputRef.current?.click();
  };

  const handleImportFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!selectedWarehouseId) {
      message.error("Vui lòng chọn kho trước khi import.");
      return;
    }
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".csv")) {
      message.error("Chỉ hỗ trợ file CSV (.csv) theo format Masan");
      return;
    }

    setImportJob(null);
    setIsImportModalOpen(true);
    importMutation.mutate(
      {
        file,
        warehouseId: selectedWarehouseId,
        onProgress: (job) => setImportJob(job),
      },
      {
        onSuccess: (job) => {
          setImportJob(job);
          if (job.status === "completed") {
            const summary =
              job.updated != null && job.updated > 0
                ? `${job.created} mới, ${job.updated} cập nhật`
                : `${job.created} sản phẩm`;
            message.success(job.message || `Đã import ${summary}`);
            setPage(1);
          } else {
            message.error(job.message || "Import thất bại");
          }
        },
        onError: (err) => {
          message.error(
            getApiErrorMessage(err, "Không thể upload file import"),
          );
          setIsImportModalOpen(false);
        },
      },
    );
  };

  const importPercent = (() => {
    if (!importJob) return importMutation.isPending ? 5 : 0;
    if (importJob.status === "completed" || importJob.status === "failed") {
      return 100;
    }
    if (importJob.total > 0) {
      return Math.min(
        99,
        Math.round((importJob.processed / importJob.total) * 100),
      );
    }
    if (importJob.status === "running") {
      return 30;
    }
    if (importJob.message && importJob.message !== "Đang chờ xử lý") {
      return 15;
    }
    return 10;
  })();

  const columns: ColumnsType<Item> = [
    {
      title: "Part_number",
      dataIndex: "sku",
      key: "sku",
      sorter: (a, b) => a.sku.localeCompare(b.sku),
    },
    {
      title: "Tên sản phẩm",
      dataIndex: "name",
      key: "name",
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: "Mô tả",
      dataIndex: "description",
      key: "description",
      sorter: (a, b) => (a.description ?? '').localeCompare(b.description ?? ''),
    },
    {
      title: "Số lượng",
      dataIndex: "quantity",
      key: "quantity",
      sorter: (a, b) => parseQuantity(a.quantity) - parseQuantity(b.quantity),
      render: (qty: number | string) => {
        const amount = parseQuantity(qty);
        return (
          <span
            className={
              amount === 0 || amount < 10
                ? "font-semibold text-orange-500"
                : "font-semibold text-brand-dark"
            }
          >
            {formatQuantity(qty)}
          </span>
        );
      },
    },
    {
      title: "Tổng giá trị",
      dataIndex: "total_price",
      key: "total_price",
      sorter: (a, b) => parseQuantity(a.total_price) - parseQuantity(b.total_price),
      render: (totalPrice: number | string) => (
        <span className="font-semibold text-brand-dark">
          {formatInventoryValue(totalPrice)}
        </span>
      ),
    },
    {
      title: "Đơn vị",
      dataIndex: "base_unit",
      key: "base_unit",
      sorter: (a, b) => a.base_unit.localeCompare(b.base_unit),
    },
    {
      title: "Ngày tạo",
      dataIndex: "created_at",
      key: "created_at",
      sorter: (a, b) => a.created_at.localeCompare(b.created_at),
      render: (date: string) => formatDate(date),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-brand-dark">Sản phẩm</h2>
        <span className="text-sm text-gray-400">
          {selectedWarehouseName ?? "Chưa chọn kho"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpiCards.map((card) => (
          <Card key={card.label}>
            <p className="text-sm text-gray-500">{card.label}</p>
            <p
              className="mt-2 text-3xl font-bold"
              style={{ color: card.color }}
            >
              {isAnalyzeLoading ? "..." : card.value}
            </p>
          </Card>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-100/50 shadow-sm">
        <div className="flex items-stretch gap-0 border-b border-stripe-hairline bg-[#eef2f6]">
          {ITEM_PAGE_TABS.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  "relative min-h-11 min-w-[160px] px-6 py-3 text-sm font-semibold transition-all",
                  isActive
                    ? "z-10 -mb-px border border-stripe-hairline border-b-white bg-white text-brand-primary shadow-[0_1px_0_0_#fff]"
                    : "mb-0 border border-transparent bg-transparent text-stripe-ink-mute hover:bg-white/40 hover:text-brand-dark",
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <Card className="!rounded-none border-0 shadow-none overflow-hidden p-0">
          {activeTab === "products" ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-5 py-4">
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
                  <Input
                    allowClear
                    prefix={<SearchOutlined className="text-gray-400" />}
                    placeholder="Tìm theo tên, Part_number, mã..."
                    value={searchInput}
                    onChange={(e) => {
                      const value = e.target.value;
                      setSearchInput(value);
                      if (!value.trim()) {
                        setSubmittedQuery("");
                        setPage(1);
                      }
                    }}
                    onPressEnter={handleSearch}
                    className="!w-72 max-w-full"
                  />
                  <Button
                    variant="secondary"
                    icon={<SearchOutlined />}
                    onClick={handleSearch}
                    loading={isItemsLoading}
                  >
                    Tìm
                  </Button>
                </div>
                <div className="flex flex-wrap items-center gap-3 shrink-0">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ITEM_IMPORT_ACCEPT}
                    className="hidden"
                    onChange={handleImportFileChange}
                  />
                  <Button
                    variant="secondary"
                    icon={<UploadOutlined />}
                    onClick={handleImportClick}
                    loading={importMutation.isPending}
                  >
                    Import CSV
                  </Button>
                  <Button
                    variant="secondary"
                    icon={<DownloadOutlined />}
                    onClick={handleDownloadImportFile}
                    loading={downloadImportFileMutation.isPending}
                  >
                    Tải CSV import
                  </Button>
                  <Button
                    variant="secondary"
                    icon={<BranchesOutlined />}
                    onClick={() => navigate('/production/routes')}
                  >
                    Cấu hình Route
                  </Button>
                  <Button
                    variant="primary"
                    icon={<PlusOutlined />}
                    onClick={handleOpenCreate}
                  >
                    Thêm sản phẩm
                  </Button>
                </div>
              </div>
              <div className="border-b border-gray-100 px-5 py-3">
                <h3 className="text-base font-semibold text-brand-dark">
                  Danh sách sản phẩm
                </h3>
              </div>
              <Table<Item>
                columns={columns}
                dataSource={itemList}
                loading={isItemsLoading}
                rowKey="id"
                onRow={(record) => ({
                  onDoubleClick: () => navigate(`/items/${record.id}`),
                })}
                rowClassName={() => "cursor-pointer select-none"}
                pagination={{
                  current: page,
                  pageSize: PAGE_SIZE,
                  total: itemList.length,
                  showSizeChanger: false,
                  showTotal: (total, range) =>
                    `Hiển thị ${range[0]}–${range[1]} / ${total} sản phẩm`,
                  onChange: (nextPage) => setPage(nextPage),
                }}
                className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold [&_.ant-table-row]:hover:bg-slate-50/50 [&_.ant-table-cell]:!text-center"
              />
            </>
          ) : (
            <div className="space-y-6 p-5">
              <div>
                <h3 className="mb-1 text-base font-semibold text-brand-dark">
                  Đồ thị tồn kho
                </h3>
        
              </div>

              {isItemsLoading ? (
                <div className="flex h-64 items-center justify-center text-brand-primary/70">
                  Đang tải dữ liệu tồn kho...
                </div>
              ) : itemList.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-slate-400">
                  Chưa có sản phẩm để hiển thị đồ thị.
                </div>
              ) : (
                <div className="space-y-4">
                  {stockLineChartChunks.map((chunk, index) => {
                    const from = index * STOCK_CHART_CHUNK_SIZE + 1;
                    const to = from + chunk.data.length - 1;
                    const inBoundCount = chunk.data.filter(
                      (row) => row.status === "ok",
                    ).length;
                    const outBoundCount = chunk.data.length - inBoundCount;
                    const gradientId = `stockOkFill-${index}`;
                    return (
                      <div
                        key={`stock-line-chart-${from}-${to}`}
                        className="rounded-xl border border-slate-200/80 border-l-4 bg-slate-50/40 p-5"
                        style={{ borderLeftColor: brand.primary }}
                      >
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                          <h4 className="text-sm font-semibold text-brand-dark">
                            Tồn kho theo sản phẩm
                            {stockLineChartChunks.length > 1
                              ? ` (${from}–${to})`
                              : ""}
                          </h4>
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-semibold"
                              style={{
                                backgroundColor: `${STOCK_COLOR_OK}1a`,
                                color: STOCK_COLOR_OK,
                              }}
                            >
                              <span
                                className="h-1.5 w-1.5 rounded-full"
                                style={{ backgroundColor: STOCK_COLOR_OK }}
                              />
                              Trong biên {inBoundCount}
                            </span>
                            <span
                              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-semibold"
                              style={{
                                backgroundColor: `${STOCK_COLOR_BAD}1a`,
                                color: STOCK_COLOR_BAD,
                              }}
                            >
                              <span
                                className="h-1.5 w-1.5 rounded-full"
                                style={{ backgroundColor: STOCK_COLOR_BAD }}
                              />
                              Ngoài biên {outBoundCount}
                            </span>
                          </div>
                        </div>
                        <StockChartLegend />
                        <ResponsiveContainer width="100%" height={440}>
                          <ComposedChart
                            data={chunk.data}
                            margin={{ top: 12, right: 12, left: 0, bottom: 48 }}
                          >
                            <defs>
                              <linearGradient
                                id={gradientId}
                                x1="0"
                                y1="0"
                                x2="0"
                                y2="1"
                              >
                                <stop
                                  offset="5%"
                                  stopColor={STOCK_COLOR_OK}
                                  stopOpacity={0.28}
                                />
                                <stop
                                  offset="95%"
                                  stopColor={STOCK_COLOR_OK}
                                  stopOpacity={0}
                                />
                              </linearGradient>
                            </defs>
                            <CartesianGrid
                              stroke="#e2e8f0"
                              strokeDasharray="0"
                              vertical={false}
                            />
                            <XAxis
                              dataKey="name"
                              tick={STOCK_CHART_AXIS_TICK}
                              interval={0}
                              angle={-35}
                              textAnchor="end"
                              height={70}
                              axisLine={{ stroke: "#e2e8f0" }}
                              tickLine={false}
                            />
                            <YAxis
                              tick={STOCK_CHART_AXIS_TICK}
                              domain={[0, chunk.yMax]}
                              allowDecimals={false}
                              axisLine={false}
                              tickLine={false}
                            />
                            <Tooltip content={<StockChartTooltip />} />
                            <Area
                              type="monotone"
                              dataKey="quantityOk"
                              name="Tồn trong biên"
                              stroke="none"
                              fill={`url(#${gradientId})`}
                              connectNulls={false}
                              legendType="none"
                              tooltipType="none"
                            />
                            <Line
                              type="monotone"
                              dataKey="quantityOk"
                              name="Tồn trong biên"
                              stroke={STOCK_COLOR_OK}
                              strokeWidth={2.5}
                              connectNulls={false}
                              dot={(props) => {
                                const point = props.payload as
                                  | StockChartPoint
                                  | undefined;
                                if (point?.status !== "ok") return null;
                                return (
                                  <QuantityStatusDot
                                    cx={props.cx}
                                    cy={props.cy}
                                    payload={point}
                                  />
                                );
                              }}
                              activeDot={{ r: 5, fill: STOCK_COLOR_OK }}
                            />
                            <Line
                              type="monotone"
                              dataKey="quantityBad"
                              name="Tồn ngoài biên"
                              stroke={STOCK_COLOR_BAD}
                              strokeWidth={3}
                              connectNulls={false}
                              dot={(props) => {
                                const point = props.payload as
                                  | StockChartPoint
                                  | undefined;
                                if (!point || point.status === "ok") return null;
                                return (
                                  <QuantityStatusDot
                                    cx={props.cx}
                                    cy={props.cy}
                                    payload={point}
                                  />
                                );
                              }}
                              activeDot={{ r: 6, fill: STOCK_COLOR_BAD }}
                            />
                          </ComposedChart>
                        </ResponsiveContainer>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
      <Modal
        open={isCreateOpen}
        onCancel={handleCloseCreate}
        footer={null}
        width={640}
        centered
        destroyOnHidden
        title={
          <span className="text-brand-dark font-semibold">
            Thêm sản phẩm mới
          </span>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          className="mt-2"
          initialValues={{ standard_quantity_per_cart: 120 }}
        >
          <Form.Item
            name="sku"
            label="Part_number (Mã Model)"
            rules={[{ required: true, message: "Vui lòng nhập Part_number!" }]}
          >
            <Input placeholder="Ví dụ: MODEL-C" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Tên sản phẩm (Model)"
            rules={[{ required: true, message: "Vui lòng nhập tên!" }]}
          >
            <Input placeholder="Ví dụ: Phôi Trục Bánh Răng" />
          </Form.Item>

          <Form.Item
            name="base_unit"
            label="Đơn vị"
            rules={[{ required: true, message: "Vui lòng chọn đơn vị!" }]}
          >
            <Select
              showSearch
              placeholder="Chọn đơn vị"
              optionFilterProp="label"
              loading={isUnitsLoading}
              options={units.map((unit) => ({
                value: unit.id,
                label: unit.name,
              }))}
            />
          </Form.Item>

          <Form.Item
            name="standard_quantity_per_cart"
            label="Tiêu chuẩn phôi / xe gá (chi tiết/rack)"
            rules={[
              { required: true, message: "Vui lòng nhập số lượng tiêu chuẩn/xe!" },
              { type: "number", min: 1, message: "Giá trị phải >= 1" },
            ]}
          >
            <InputNumber min={1} precision={0} placeholder="Ví dụ: 120" className="w-full" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Mô tả"
            rules={[{ required: true, message: "Vui lòng nhập mô tả!" }]}
          >
            <Input placeholder="Ví dụ: Thép cuộn" />
          </Form.Item>

          <Form.Item label="Thông tin bổ sung (tùy chọn)">
            <Form.List name="detailEntries">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <div
                      key={key}
                      className="mb-2 flex w-full items-start gap-2"
                    >
                      <Form.Item
                        {...restField}
                        name={[name, "key"]}
                        rules={[{ required: true, message: "Nhập tên trường" }]}
                        className="!mb-0 flex-1"
                      >
                        <Input placeholder="Tên (vd: cavity_number)" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, "value"]}
                        rules={[{ required: true, message: "Nhập giá trị" }]}
                        className="!mb-0 flex-1"
                      >
                        <Input placeholder="Giá trị (vd: 1, 2, 3)" />
                      </Form.Item>
                      <MinusCircleOutlined
                        className="text-red-400 cursor-pointer"
                        onClick={() => remove(name)}
                      />
                    </div>
                  ))}
                  <Button
                    variant="secondary"
                    onClick={() => add({ key: "", value: "" })}
                    icon={<PlusOutlined />}
                    block
                  >
                    Thêm trường
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>

          <Form.Item className="mb-0 flex justify-end">
            <Space>
              <Button variant="secondary" onClick={handleCloseCreate}>
                Hủy
              </Button>
              <Button htmlType="submit" variant="primary">
                Lưu lại
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={isImportModalOpen}
        onCancel={() => {
          if (importMutation.isPending) return;
          setIsImportModalOpen(false);
        }}
        footer={
          <Button
            variant="primary"
            disabled={importMutation.isPending}
            onClick={() => setIsImportModalOpen(false)}
          >
            Đóng
          </Button>
        }
        closable={!importMutation.isPending}
        mask={{ closable: !importMutation.isPending }}
        title={
          <span className="text-brand-dark font-semibold">
            Import sản phẩm từ CSV (Masan)
          </span>
        }
      >
        <div className="space-y-3 py-2">
          <p className="text-sm text-slate-600">
            Warehouse: <strong>{selectedWarehouseName}</strong>
            {importJob?.filename ? (
              <>
                {" "}
                · File: <strong>{importJob.filename}</strong>
              </>
            ) : null}
          </p>
          <p className="text-xs text-slate-500">
            File CSV cần có header (dòng 2 nếu có dòng tiêu đề):{" "}
            <strong>{ITEM_IMPORT_REQUIRED_COLUMNS.join(", ")}</strong>
          </p>
          <Progress
            percent={importPercent}
            status={
              importJob?.status === "failed"
                ? "exception"
                : importJob?.status === "completed"
                  ? "success"
                  : "active"
            }
          />
          <p className="text-sm text-slate-700">
            {importJob?.message ||
              (importMutation.isPending
                ? "Đang upload và xử lý file…"
                : "Chờ bắt đầu…")}
          </p>
          {importJob && (
            <p className="text-xs text-slate-500">
              Status: {importJob.status} · processed {importJob.processed}
              {importJob.total ? ` / ${importJob.total}` : ""} · created{" "}
              {importJob.created}
              {importJob.updated ? ` · updated ${importJob.updated}` : ""}
              {importJob.error_count
                ? ` · errors ${importJob.error_count}`
                : ""}
            </p>
          )}
          {importJob?.errors?.length ? (
            <div className="max-h-48 overflow-auto rounded border border-slate-100 bg-slate-50 p-3 text-xs text-slate-700">
              {importJob.errors.slice(0, 20).map((err, idx) => (
                <div key={`${err.row}-${err.sku}-${idx}`} className="mb-1">
                  Dòng {err.row}
                  {err.sku ? ` (${err.sku})` : ""}: {err.message}
                </div>
              ))}
              {importJob.error_count > importJob.errors.length && (
                <div className="mt-2 text-slate-500">
                  … và {importJob.error_count - importJob.errors.length} lỗi
                  khác
                </div>
              )}
            </div>
          ) : null}
        </div>
      </Modal>
    </div>
  );
}
