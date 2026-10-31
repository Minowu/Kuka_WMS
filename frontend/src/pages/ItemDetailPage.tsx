import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  EditOutlined,
  MinusCircleOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import {
  Card,
  Button,
  Table,
  Modal,
  Form,
  Input,
  InputNumber,
  Space,
  message,
  Select,
} from "@/components/ui";
import { Tag } from "antd";
import {
  useDeactivateItem,
  useItemById,
  useUpdateItem,
} from "@/hooks/useItem";
import type { ItemStock } from "@/types/item";
import { useAppStore } from "@/store/useAppStore";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { useWarehouses } from "@/hooks/useWarehouse";
import { DetailView } from "@/components/ui/DetailView";
import dayjs from "dayjs";
import type { Item } from "@/types/item";
import type { DetailFieldSchema } from "@/components/ui/DetailView";
import { formatQuantity, parseQuantity } from "@/utils/formatQuantity";

function formatDetailEntryValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function ItemDetailsView({ details }: { details?: Record<string, unknown> }) {
  const entries = Object.entries(details ?? {});
  if (entries.length === 0) {
    return <span className="text-gray-400">Không có</span>;
  }
  return (
    <dl className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="min-w-0">
          <dt className="text-sm text-gray-500">{key}</dt>
          <dd className="mt-0.5 text-sm font-medium text-brand-dark break-words">
            {formatDetailEntryValue(value) || "—"}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** Primary product metadata (quantities, unit, description) — left column. */
export const ITEM_DETAIL_PRIMARY_FIELD_COUNT = 6;

export const itemDetailFields: DetailFieldSchema<Item>[] = [
  {
    key: "quantity",
    label: "Số lượng tồn",
    render: (item) => {
      const amount = parseQuantity(item.quantity);
      return (
        <span
          className={
            amount === 0
              ? "font-semibold text-orange-500"
              : "font-semibold"
          }
        >
          {formatQuantity(item.quantity)}
        </span>
      );
    },
  },
  {
    key: "standard_quantity_per_cart",
    label: "Tiêu chuẩn phôi / xe gá",
    accessor: (item) => `${item.standard_quantity_per_cart ?? 120} chi tiết/xe`,
  },

  {
    key: "description",
    label: "Mô tả",
    accessor: (item) => item.description,
  },
  {
    key: "created_at",
    label: "Ngày khởi tạo",
    render: (item) => formatDate(item.created_at),
  },
  {
    key: "updated_at",
    label: "Ngày cập nhật",
    render: (item) => formatDate(item.updated_at),
  },
  {
    key: "details",
    label: "Thông tin bổ sung",
    render: (item) => <ItemDetailsView details={item.details} />,
  },
];

type ItemFormValues = {
  name: string;
  sku: string;
  standard_quantity_per_cart: number;
  description?: string;
  quantity: number;
  detailEntries?: { key: string; value: string }[];
};

function formatDate(date?: string | null) {
  if (!date) return "—";
  return dayjs(date).format("DD/MM/YYYY");
}

const TABLE_CLASS =
  "[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold [&_.ant-table-thead_th]:!text-base [&_.ant-table-tbody_td]:!text-base [&_.ant-table-thead_th]:!py-3 [&_.ant-table-tbody_td]:!py-3 [&_.ant-table-row]:hover:bg-slate-50/50 [&_.ant-table-cell]:!text-center";

const locationColumns: ColumnsType<ItemStock> = [
  {
    title: "Mã Xe Gá (WIP)",
    dataIndex: "container_code",
    key: "container_code",
    render: (code: string | null | undefined) =>
      code ? (
        <Tag color="cyan" className="font-semibold text-sm">
          {code}
        </Tag>
      ) : (
        <span className="text-gray-400">—</span>
      ),
  },
  {
    title: "Vị Trí Đỗ Hiện Tại",
    dataIndex: "location_name",
    key: "location_name",
    render: (name: string | null | undefined, row) =>
      name || row.location_code || (row.location_id ? `#${row.location_id}` : "—"),
  },
  {
    title: "Công Đoạn Hiện Tại",
    dataIndex: "current_stage_level",
    key: "current_stage_level",
    align: "center",
    render: (level: number | undefined) => {
      const stage = Number(level ?? 0);
      if (stage === 0) {
        return <Tag color="default">CĐ 0: Phôi Thô</Tag>;
      }
      return <Tag color="blue">{`CĐ ${stage}: Hoàn Thành B1-${stage}`}</Tag>;
    },
  },
  {
    title: "Số Lượng Phôi",
    dataIndex: "quantity",
    key: "quantity",
    align: "center",
    render: (qty: number | string) => (
      <span className="font-semibold text-brand-dark">
        {formatQuantity(qty)}
      </span>
    ),
  },
  {
    title: "Trạng Thái",
    dataIndex: "status",
    key: "status",
    align: "center",
    render: (status: string) => {
      if (status === "available") {
        return <Tag color="success">Sẵn sàng</Tag>;
      }
      if (status === "locked" || status === "in_transit") {
        return <Tag color="warning">Đang điều phối AGV</Tag>;
      }
      return <Tag>{status}</Tag>;
    },
  },
];

export default function ItemDetailPage() {
  const navigate = useNavigate();
  const { selectedWarehouseId } = useAppStore();
  const { data: warehouses = [] } = useWarehouses();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [form] = Form.useForm<ItemFormValues>();
  const { id } = useParams<{ id: string }>();
  const itemId = Number(id) || 0;
  const updateMutation = useUpdateItem();
  const deactivateMutation = useDeactivateItem();
  const { data } = useItemById(itemId);
  const item = data?.item;
  const stocks = data?.stocks ?? [];

  const warehouseName =
    warehouses.find((z) => z.id === selectedWarehouseId)?.name ?? "Chưa chọn kho";

  const handleOpenEdit = () => {
    if (!item) return;
    form.setFieldsValue({
      name: item.name,
      sku: item.sku,
      standard_quantity_per_cart: item.standard_quantity_per_cart ?? 120,
      description: item.description ?? "",
      quantity: parseQuantity(item.quantity),
      detailEntries: Object.entries(item.details ?? {}).map(([key, value]) => ({
        key,
        value: formatDetailEntryValue(value),
      })),
    });
    setIsEditOpen(true);
  };
  const handleCloseEdit = () => {
    setIsEditOpen(false);
    form.resetFields();
  };
  const handleSubmit = (values: ItemFormValues) => {
    if (!item) return;

    const details = Object.fromEntries(
      (values.detailEntries ?? [])
        .map(({ key, value }) => [key.trim(), value.trim()] as const)
        .filter(([key]) => key.length > 0),
    );

    updateMutation.mutate(
      {
        id: item.id,
        data: {
          name: values.name.trim(),
          description: values.description?.trim() || null,
          standard_quantity_per_cart: Number(values.standard_quantity_per_cart ?? 120),
          details,
        },
      },
      {
        onSuccess: () => {
          message.success("Cập nhật sản phẩm thành công!");
          handleCloseEdit();
        },
        onError: (err) => {
          message.error(getApiErrorMessage(err, "Không thể cập nhật sản phẩm"));
        },
      },
    );
  };

  const handleDelete = () => {
    if (!item) return;

    Modal.confirmDelete({
      content: `Bạn có chắc chắn muốn xóa sản phẩm "${item.name}" (${item.sku})?`,
      onOk: () =>
        new Promise<void>((resolve, reject) => {
          deactivateMutation.mutate(item.id, {
            onSuccess: () => {
              message.success("Xóa sản phẩm thành công!");
              navigate("/items");
              resolve();
            },
            onError: (err) => {
              message.error(getApiErrorMessage(err, "Không thể xóa sản phẩm"));
              reject();
            },
          });
        }),
    });
  };

  if (!item) {
    return (
      <div className="space-y-4">
        <Button
          variant="secondary"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/items")}
        >
          Quay lại
        </Button>
        <Card>
          <p className="text-gray-500">
            Không tìm thấy sản phẩm với id &quot;{id}&quot;.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/items")}
          >
            Quay lại
          </Button>
          <h2 className="text-2xl font-bold text-brand-dark">
            Chi tiết sản phẩm
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">{warehouseName}</span>
        </div>
      </div>

      <Card className="rounded-xl overflow-hidden">
        <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-5 py-4">
          <div className="min-w-0">
            <p className="text-lg font-semibold text-brand-primary">
              {item.sku}
            </p>
            <p className="text-base text-brand-dark">{item.name}</p>
          </div>
          <Space className="shrink-0">
            <Button
              variant="edit"
              icon={<EditOutlined />}
              onClick={handleOpenEdit}
            >
              Chỉnh sửa
            </Button>
            <Button
              variant="dangerText"
              icon={<DeleteOutlined />}
              onClick={handleDelete}
              loading={deactivateMutation.isPending}
              disabled={deactivateMutation.isPending}
              className="hover:bg-red-50 rounded-lg"
            >
              Xóa
            </Button>
          </Space>
        </div>

        <div className="grid grid-cols-1 gap-x-8 gap-y-4 border-b border-gray-100 px-5 py-2 lg:grid-cols-2">
          <DetailView
            data={item}
            fields={itemDetailFields.slice(0, ITEM_DETAIL_PRIMARY_FIELD_COUNT)}
          />
          <DetailView
            data={item}
            fields={itemDetailFields.slice(ITEM_DETAIL_PRIMARY_FIELD_COUNT)}
          />
        </div>

        <div className="border-b border-gray-100 px-5 py-4">
          <h3 className="text-base font-semibold text-brand-dark">
            Tồn kho theo vị trí
          </h3>
        </div>
        <Table<ItemStock>
          columns={locationColumns}
          dataSource={stocks}
          rowKey="id"
          pagination={false}
          size="middle"
          className={TABLE_CLASS}
          locale={{ emptyText: "Chưa có tồn kho tại vị trí nào" }}
        />
      </Card>

      <Modal
        open={isEditOpen}
        onCancel={handleCloseEdit}
        footer={null}
        width={640}
        destroyOnHidden
        title={
          <div className="flex items-center justify-between gap-4 pr-8">
            <span className="text-brand-dark font-semibold">
              Chỉnh sửa thông tin sản phẩm
            </span>
            <span className="text-sm font-medium text-brand-primary">
              {item.sku}
            </span>
          </div>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          className="mt-2"
        >
          <Form.Item
            name="name"
            label="Tên sản phẩm"
            rules={[{ required: true, message: "Vui lòng nhập tên!" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="sku"
            label="Part_number"
            rules={[{ required: true, message: "Vui lòng nhập Part_number!" }]}
          >
            <Input disabled />
          </Form.Item>
          <Form.Item
            name="quantity"
            label="Số lượng"
            rules={[{ required: true, message: "Vui lòng nhập số lượng!" }]}
          >
            <InputNumber disabled min={0} precision={0} />
          </Form.Item>
          <Form.Item
            name="standard_quantity_per_cart"
            label="Tiêu chuẩn phôi / xe gá (chi tiết/xe)"
            rules={[
              { required: true, message: "Vui lòng nhập số lượng tiêu chuẩn/xe!" },
              { type: "number", min: 1, message: "Giá trị phải >= 1" },
            ]}
          >
            <InputNumber min={1} precision={0} placeholder="Ví dụ: 120" className="w-full" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Mô tả kỹ thuật"
          >
            <Input placeholder="Mô tả kỹ thuật (tùy chọn)" />
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
                        className="!mb-0 flex-1"
                      >
                        <Input placeholder="Tên (vd: cavity_number)" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, "value"]}
                        className="!mb-0 flex-1"
                      >
                        <Input placeholder="Giá trị (vd: 1, 2, 3)" />
                      </Form.Item>
                      <MinusCircleOutlined
                        className="mt-2 shrink-0 cursor-pointer text-red-400"
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
              <Button variant="secondary" onClick={handleCloseEdit}>
                Hủy
              </Button>
              <Button
                htmlType="submit"
                variant="primary"
                loading={updateMutation.isPending}
                disabled={updateMutation.isPending}
              >
                Lưu thay đổi
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
