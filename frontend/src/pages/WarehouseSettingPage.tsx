import { useState } from 'react';
import { Card, Table, Button, Modal, Space, Form, Input, message } from '@/components/ui';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import {
  useWarehouses,
  useCreateWarehouse,
  useUpdateWarehouse,
  useDeleteWarehouse,
} from '@/hooks/useWarehouse';
import type { Warehouse } from '@/types/warehouse';
import Hero from '@/components/shared/Hero';
import { getApiErrorMessage } from '@/utils/apiErrorMessage';

export default function WarehouseSettingPage() {
  const { data: warehouses, isLoading, error } = useWarehouses();
  const createMutation = useCreateWarehouse();
  const updateMutation = useUpdateWarehouse();
  const deleteMutation = useDeleteWarehouse();

  const [form] = Form.useForm();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingWarehouse, setEditingWarehouse] = useState<Warehouse | null>(null);
  const hasExistingWarehouse = (warehouses || []).length >= 1;

  const handleOpenCreate = () => {
    setEditingWarehouse(null);
    form.resetFields();
    setIsModalOpen(true);
  };

  const handleOpenEdit = (record: Warehouse) => {
    setEditingWarehouse(record);
    form.setFieldsValue({
      code: record.code,
      name: record.name,
      description: record.description,
    });
    setIsModalOpen(true);
  };

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: 'Xác nhận xóa',
      content: 'Bạn có chắc chắn muốn xóa kho hàng này không?',
      okText: 'Xóa',
      okType: 'danger',
      cancelText: 'Hủy',
      onOk: () => {
        return new Promise((resolve) => {
          deleteMutation.mutate(id, {
            onSuccess: () => {
              message.success('Xóa kho hàng thành công!');
              resolve(null);
            },
            onError: (error) => {
              message.error(getApiErrorMessage(error, 'Không thể xóa kho hàng'));
              resolve(null);
            },
          });
        });
      },
    });
  };

  const handleSubmit = (values: {
    code: string;
    name?: string;
    description?: string;
  }) => {
    if (editingWarehouse) {
      updateMutation.mutate(
        { id: editingWarehouse.id, data: values },
        {
          onSuccess: () => {
            message.success('Cập nhật kho hàng thành công!');
            setIsModalOpen(false);
            form.resetFields();
          },
          onError: (error) => {
            message.error(getApiErrorMessage(error, 'Không thể cập nhật kho hàng'));
          },
        },
      );
    } else {
      createMutation.mutate(values, {
        onSuccess: () => {
          message.success('Thêm kho hàng thành công!');
          setIsModalOpen(false);
          form.resetFields();
        },
        onError: (error) => {
          message.error(getApiErrorMessage(error, 'Không thể thêm kho hàng mới'));
        },
      });
    }
  };

  const columns = [
    {
      title: 'Mã Kho',
      dataIndex: 'code',
      key: 'code',
      render: (text: string) => (
        <span className="font-semibold text-brand-primary">{text}</span>
      ),
    },
    {
      title: 'Tên Kho',
      dataIndex: 'name',
      key: 'name',
      className: 'font-medium text-slate-700',
    },
    {
      title: 'Mô tả',
      dataIndex: 'description',
      key: 'description',
      className: 'text-slate-500',
    },
    {
      title: 'Thao tác',
      key: 'action',
      width: 150,
      render: (_: unknown, record: Warehouse) => (
        <Space size="middle">
          <Button
            variant="edit"
            icon={<EditOutlined className="text-brand-primary" />}
            onClick={() => handleOpenEdit(record)}
            title="Sửa thông tin xưởng"
          />
          {hasExistingWarehouse ? (
            <span
              className="text-xs text-slate-400 italic cursor-not-allowed select-none px-2 py-1 bg-slate-100 rounded"
              title="Không thể xóa kho duy nhất của hệ thống"
            >
              Kho mặc định
            </span>
          ) : (
            <Button
              variant="dangerText"
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              className="hover:bg-red-50 rounded-lg"
              title="Xóa"
            />
          )}
        </Space>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="text-brand-primary/70 font-medium">
          Đang tải danh sách kho...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl">
        Không thể kết nối đến máy chủ. Vui lòng tải lại trang!
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Hero
        title="Quản lý Kho Hàng"
        extra={
          hasExistingWarehouse ? (
            <span className="text-xs font-semibold px-3 py-1.5 bg-blue-50 text-brand-primary border border-blue-200/60 rounded-lg">
              🏭 Hệ thống vận hành tập trung 1 Xưởng duy nhất
            </span>
          ) : (
            <Button
              onClick={handleOpenCreate}
              icon={<PlusOutlined />}
              className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none !h-10 !rounded-lg font-semibold flex items-center"
            >
              Thêm Kho Mới
            </Button>
          )
        }
      />

      <Card className="shadow-sm border-gray-100/50 rounded-xl overflow-hidden">
        <Table
          columns={columns}
          dataSource={warehouses}
          rowKey="id"
          pagination={false}
          className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold [&_.ant-table-row]:hover:bg-slate-50/50 [&_.ant-table-cell]:!text-center"
        />
      </Card>

      <Modal
        title={editingWarehouse ? 'Cập nhật Kho Hàng' : 'Thêm Kho Mới'}
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          className="mt-4"
        >
          <Form.Item
            name="code"
            label="Mã Kho"
            rules={[{ required: true, message: 'Vui lòng nhập mã kho!' }]}
          >
            <Input
              placeholder="Ví dụ: KHO_A"
              disabled={!!editingWarehouse}
            />
          </Form.Item>

          <Form.Item
            name="name"
            label="Tên Kho"
            rules={[{ required: true, message: 'Vui lòng nhập tên kho!' }]}
          >
            <Input placeholder="Ví dụ: Kho tổng miền Bắc" />
          </Form.Item>

          <Form.Item name="description" label="Mô tả">
            <Input.TextArea
              rows={3}
              placeholder="Mô tả chi tiết về kho hàng"
            />
          </Form.Item>

          <Form.Item className="mb-0 flex justify-end">
            <Space>
              <Button onClick={() => setIsModalOpen(false)}>Hủy</Button>
              <Button
                htmlType="submit"
                loading={createMutation.isPending || updateMutation.isPending}
                className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none"
              >
                {editingWarehouse ? 'Cập nhật' : 'Lưu lại'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
