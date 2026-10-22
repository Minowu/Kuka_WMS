import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  BranchesOutlined,
  EyeOutlined,
  MinusCircleOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";
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
} from "@/components/ui";
import { Popconfirm, Tooltip, Tag } from "antd";
import {
  useItems,
  useCreateItem,
  useUpdateItem,
  useDeactivateItem,
} from "@/hooks/useItem";
import { useAppStore } from "@/store/useAppStore";
import { useWarehouses } from "@/hooks/useWarehouse";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import { formatQuantity } from "@/utils/formatQuantity";
import type { Item, CreateItemInput } from "@/types/item";
import dayjs from "dayjs";

const PAGE_SIZE = 20;

type CreateItemFormValues = Omit<CreateItemInput, "details"> & {
  detailEntries?: { key: string; value: string }[];
};

function formatDate(date?: string | null) {
  if (!date) return "—";
  return dayjs(date).format("DD/MM/YYYY HH:mm");
}

export default function ItemPage() {
  const navigate = useNavigate();
  const { selectedWarehouseId } = useAppStore();
  const { data: warehouses = [] } = useWarehouses();

  const selectedWarehouse = warehouses.find((w) => w.id === selectedWarehouseId);
  const selectedWarehouseName =
    selectedWarehouse?.name ?? selectedWarehouse?.code ?? "Toàn bộ phân xưởng";

  const [searchInput, setSearchInput] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);

  // Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Item | null>(null);

  const [createForm] = Form.useForm<CreateItemFormValues>();
  const [editForm] = Form.useForm();

  // Mutations
  const createMutation = useCreateItem();
  const updateMutation = useUpdateItem();
  const deleteMutation = useDeactivateItem();

  // Fetch Items
  const { data, isLoading: isItemsLoading } = useItems({
    warehouse_id: selectedWarehouseId,
    q: submittedQuery || undefined,
    page_size: 100,
  });

  const itemList = data?.items ?? [];

  const handleSearch = () => {
    setSubmittedQuery(searchInput.trim());
    setPage(1);
  };

  const handleOpenCreate = () => {
    createForm.resetFields();
    createForm.setFieldsValue({
      standard_quantity_per_cart: 120,
    });
    setIsCreateOpen(true);
  };

  const handleCreate = (values: CreateItemFormValues) => {
    const details = Object.fromEntries(
      (values.detailEntries ?? [])
        .map(({ key, value }) => [key.trim(), value.trim()] as const)
        .filter(([key]) => key.length > 0),
    );
    const targetWarehouseId = selectedWarehouseId || warehouses[0]?.id || 1;

    createMutation.mutate(
      {
        sku: values.sku.trim(),
        name: values.name.trim(),
        description: values.description?.trim() || null,
        standard_quantity_per_cart: Number(values.standard_quantity_per_cart ?? 120),
        warehouse_id: targetWarehouseId,
        details,
      },
      {
        onSuccess: () => {
          message.success("Thêm Model sản phẩm thành công!");
          setIsCreateOpen(false);
          setPage(1);
        },
        onError: (err) => {
          message.error(getApiErrorMessage(err, "Không thể thêm Model sản phẩm"));
        },
      },
    );
  };

  const handleOpenEdit = (record: Item) => {
    setEditingItem(record);
    editForm.resetFields();
    editForm.setFieldsValue({
      sku: record.sku,
      name: record.name,
      standard_quantity_per_cart: record.standard_quantity_per_cart ?? 120,
      description: record.description ?? "",
    });
  };

  const handleUpdate = async () => {
    if (!editingItem) return;
    try {
      const values = await editForm.validateFields();
      await updateMutation.mutateAsync({
        id: editingItem.id,
        data: {
          name: values.name.trim(),
          description: values.description?.trim() || null,
          standard_quantity_per_cart: Number(values.standard_quantity_per_cart ?? 120),
        },
      });
      message.success("Cập nhật Model sản phẩm thành công!");
      setEditingItem(null);
    } catch (err: any) {
      message.error(getApiErrorMessage(err, "Không thể cập nhật Model sản phẩm"));
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    try {
      await deleteMutation.mutateAsync(itemId);
      message.success("Đã xóa Model sản phẩm thành công!");
    } catch (err: any) {
      message.error(
        getApiErrorMessage(
          err,
          "Không thể xóa Model: có thể đang có xe gá phôi WIP hoặc quy trình Route đang liên kết.",
        ),
      );
    }
  };

  const columns: ColumnsType<Item> = [
    {
      title: "Part Number (Mã Model)",
      dataIndex: "sku",
      key: "sku",
      width: 180,
      sorter: (a, b) => a.sku.localeCompare(b.sku),
      render: (sku: string) => (
        <span className="font-mono font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded border border-sky-200">
          {sku}
        </span>
      ),
    },
    {
      title: "Tên Model / Chi Tiết",
      dataIndex: "name",
      key: "name",
      className: "font-medium text-slate-800",
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: "Tiêu Chuẩn / Xe",
      dataIndex: "standard_quantity_per_cart",
      key: "standard_quantity_per_cart",
      width: 160,
      align: "center",
      render: (val: number) => (
        <Tag color="cyan" className="font-semibold px-2 py-0.5">
          {val || 120} phôi/xe
        </Tag>
      ),
    },
    {
      title: "Tồn Phôi WIP",
      dataIndex: "quantity",
      key: "quantity",
      width: 140,
      align: "center",
      render: (qty: number) => {
        const val = Number(qty || 0);
        return (
          <span
            className={`font-semibold ${
              val > 0 ? "text-emerald-600" : "text-slate-400"
            }`}
          >
            {formatQuantity(val)} phôi
          </span>
        );
      },
    },
    {
      title: "Mô Tả Kỹ Thuật",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (desc: string) => desc || <span className="text-slate-400">—</span>,
    },
    {
      title: "Ngày Tạo",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      align: "center",
      render: (date: string) => (
        <span className="text-slate-500 text-xs">{formatDate(date)}</span>
      ),
    },
    {
      title: "Thao Tác",
      key: "actions",
      width: 150,
      align: "center",
      render: (_, record) => (
        <Space onClick={(e) => e.stopPropagation()} size="small">
          <Tooltip title="Xem chi tiết & xe gá phôi WIP">
            <Button
              size="small"
              variant="outline"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/items/${record.id}`)}
            />
          </Tooltip>

          <Tooltip title="Chỉnh sửa Model">
            <Button
              size="small"
              variant="outline"
              icon={<EditOutlined className="text-amber-600" />}
              onClick={() => handleOpenEdit(record)}
            />
          </Tooltip>

          <Popconfirm
            title="Xác nhận xóa Model sản phẩm?"
            description={`Bạn có chắc muốn xóa Model '${record.sku}' không?`}
            onConfirm={() => handleDeleteItem(record.id)}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Xóa Model">
              <Button
                size="small"
                variant="outline"
                className="text-red-500 hover:text-red-600 hover:border-red-300"
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-100 text-sky-700 flex items-center justify-center text-xl">
              <AppstoreOutlined />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-800">
                Danh Mục Model Sản Phẩm
              </h2>
              <p className="text-sm text-slate-500">
                Quản lý các loại chi tiết, phôi gia công cơ khí và tiêu chuẩn xếp xe gá
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            icon={<BranchesOutlined />}
            onClick={() => navigate("/production/routes")}
          >
            Cấu hình Quy trình Route
          </Button>

          <Button
            variant="primary"
            icon={<PlusOutlined />}
            onClick={handleOpenCreate}
          >
            Thêm Model Mới
          </Button>
        </div>
      </div>

      {/* Main Table Card */}
      <Card className="rounded-xl border border-gray-100 shadow-sm overflow-hidden p-0">
        {/* Filter Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 px-5 py-3.5 bg-slate-50/50">
          <div className="flex items-center gap-2">
            <Input
              allowClear
              prefix={<SearchOutlined className="text-gray-400" />}
              placeholder="Tìm theo Part Number, tên Model..."
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
              className="!w-80 max-w-full"
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

          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span>Khu vực: </span>
            <Tag color="blue" className="font-medium">
              {selectedWarehouseName}
            </Tag>
            <span className="text-slate-300">|</span>
            <span>Tổng số: </span>
            <strong className="text-slate-700">{itemList.length}</strong> Model
          </div>
        </div>

        {/* Data Table */}
        <Table<Item>
          columns={columns}
          dataSource={itemList}
          loading={isItemsLoading}
          rowKey="id"
          onRow={(record) => ({
            onDoubleClick: () => navigate(`/items/${record.id}`),
          })}
          rowClassName={() => "cursor-pointer hover:bg-slate-50/80 transition-colors"}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total: itemList.length,
            showSizeChanger: false,
            showTotal: (total, range) =>
              `Hiển thị ${range[0]}–${range[1]} / ${total} Model sản phẩm`,
            onChange: (nextPage) => setPage(nextPage),
          }}
          className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold"
        />
      </Card>

      {/* Modal Thêm Model Mới */}
      <Modal
        open={isCreateOpen}
        onCancel={() => setIsCreateOpen(false)}
        footer={null}
        width={560}
        centered
        destroyOnHidden
        title={
          <div className="flex items-center gap-2 text-slate-800 text-lg font-bold">
            <PlusOutlined className="text-sky-600" />
            Thêm Model Sản Phẩm Mới
          </div>
        }
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreate}
          className="mt-4 space-y-3"
          initialValues={{ standard_quantity_per_cart: 120 }}
        >
          <Form.Item
            name="sku"
            label="Part Number (Mã Model)"
            rules={[{ required: true, message: "Vui lòng nhập Part Number!" }]}
          >
            <Input placeholder="Ví dụ: PART-A101" className="uppercase font-mono" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Tên Model / Chi Tiết"
            rules={[{ required: true, message: "Vui lòng nhập tên Model!" }]}
          >
            <Input placeholder="Ví dụ: Trục then hoa 6 cạnh" />
          </Form.Item>

          <Form.Item
            name="standard_quantity_per_cart"
            label="Tiêu chuẩn phôi / xe gá (chi tiết/rack)"
            rules={[
              { required: true, message: "Vui lòng nhập số lượng tiêu chuẩn/xe!" },
              { type: "number", min: 1, message: "Giá trị phải >= 1" },
            ]}
          >
            <InputNumber
              min={1}
              precision={0}
              placeholder="120"
              className="w-full"
            />
          </Form.Item>

          <Form.Item name="description" label="Mô tả kỹ thuật (tùy chọn)">
            <Input.TextArea
              rows={2}
              placeholder="Ví dụ: Thép hợp kim C45 tôi cao tần, mạ kẽm..."
            />
          </Form.Item>

          <Form.Item label="Thuộc tính kỹ thuật mở rộng (tùy chọn)">
            <Form.List name="detailEntries">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <div key={key} className="mb-2 flex w-full items-center gap-2">
                      <Form.Item
                        {...restField}
                        name={[name, "key"]}
                        className="!mb-0 flex-1"
                      >
                        <Input placeholder="Tên thông số (vd: cavity_number)" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, "value"]}
                        className="!mb-0 flex-1"
                      >
                        <Input placeholder="Giá trị (vd: 4)" />
                      </Form.Item>
                      <MinusCircleOutlined
                        className="text-red-400 hover:text-red-600 cursor-pointer text-base"
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
                    Thêm thông số
                  </Button>
                </>
              )}
            </Form.List>
          </Form.Item>

          <Form.Item className="mb-0 pt-2 flex justify-end">
            <Space>
              <Button variant="secondary" onClick={() => setIsCreateOpen(false)}>
                Hủy
              </Button>
              <Button
                htmlType="submit"
                variant="primary"
                loading={createMutation.isPending}
              >
                Tạo Model
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal Chỉnh Sửa Model */}
      <Modal
        open={!!editingItem}
        onCancel={() => setEditingItem(null)}
        footer={null}
        width={560}
        centered
        title={
          <div className="flex items-center gap-2 text-slate-800 text-lg font-bold">
            <EditOutlined className="text-amber-500" />
            Chỉnh Sửa Model Sản Phẩm
          </div>
        }
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdate}
          className="mt-4 space-y-3"
        >
          <Form.Item name="sku" label="Part Number (Mã Model)">
            <Input disabled className="uppercase font-mono bg-slate-50 text-slate-500" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Tên Model / Chi Tiết"
            rules={[{ required: true, message: "Vui lòng nhập tên sản phẩm!" }]}
          >
            <Input placeholder="Ví dụ: Trục then hoa 6 cạnh" />
          </Form.Item>

          <Form.Item
            name="standard_quantity_per_cart"
            label="Tiêu chuẩn phôi / xe gá (chi tiết/rack)"
            rules={[
              { required: true, message: "Vui lòng nhập số lượng tiêu chuẩn/xe!" },
              { type: "number", min: 1, message: "Giá trị phải >= 1" },
            ]}
          >
            <InputNumber
              min={1}
              precision={0}
              placeholder="120"
              className="w-full"
            />
          </Form.Item>

          <Form.Item name="description" label="Mô tả kỹ thuật">
            <Input.TextArea
              rows={3}
              placeholder="Mô tả chi tiết kỹ thuật phôi..."
            />
          </Form.Item>

          <Form.Item className="mb-0 pt-2 flex justify-end">
            <Space>
              <Button variant="secondary" onClick={() => setEditingItem(null)}>
                Hủy
              </Button>
              <Button
                htmlType="submit"
                variant="primary"
                loading={updateMutation.isPending}
              >
                Lưu Thay Đổi
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
