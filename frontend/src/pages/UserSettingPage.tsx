import { useState } from "react";
import {
  Card,
  Table,
  Button,
  Modal,
  Space,
  Form,
  Input,
  message,
  Select,
} from "@/components/ui";
import { Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, ClusterOutlined } from "@ant-design/icons";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import StationAssignmentModal from "@/pages/components/StationAssignmentModal";
import {
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
} from "@/hooks/useAuth";
import {
  ROLE_OPTIONS,
  type CreateUserInput,
  type UpdateUserInput,
  type User,
} from "@/types/auth";
import Hero from "@/components/shared/Hero";
import dayjs from "dayjs";

type UserFormValues = {
  username: string;
  email: string;
  role_id: number;
  password?: string;
  password_confirm?: string;
};

const ADMIN_ROLE_ID = 2;

function isAdminUser(user: User | null): boolean {
  return !!user?.roles?.some((r) => r.name === "admin");
}

function getRoleTag(user: User) {
  const roleNames = user.roles?.map((r) => r.name) || [];
  if (roleNames.includes("admin")) {
    return <Tag color="blue" className="font-semibold px-2 py-0.5">Quản trị viên (Admin)</Tag>;
  }
  if (roleNames.includes("operator_raw")) {
    return <Tag color="purple" className="font-semibold px-2 py-0.5">Cấp Phôi (Nguyên Liệu)</Tag>;
  }
  if (roleNames.includes("operator_cnc")) {
    return <Tag color="cyan" className="font-semibold px-2 py-0.5">Vận Hành CNC</Tag>;
  }
  if (roleNames.includes("operator_washing")) {
    return <Tag color="green" className="font-semibold px-2 py-0.5">Khu Tẩy Rửa</Tag>;
  }
  return <Tag color="orange" className="font-semibold px-2 py-0.5">Công Nhân (Operator)</Tag>;
}

export default function UserSettingPage() {
  const { data: users, isLoading } = useUser();
  const createMutation = useCreateUser();
  const updateMutation = useUpdateUser();
  const deleteMutation = useDeleteUser();

  const [form] = Form.useForm<UserFormValues>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [stationModalUser, setStationModalUser] = useState<User | null>(null);

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingUser(null);
    form.resetFields();
  };

  const handleOpenCreate = () => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({ role_id: 4 }); // Mặc định là Operator CNC
    setIsModalOpen(true);
  };

  const handleOpenEdit = (record: User) => {
    setEditingUser(record);
    const roleId = record.roles?.[0]?.id ?? 1;
    form.setFieldsValue({
      username: record.username,
      email: record.email,
      role_id: roleId,
      password: undefined,
      password_confirm: undefined,
    });
    setIsModalOpen(true);
  };

  const handleDelete = (id: number) => {
    Modal.confirm({
      title: "Xác nhận xóa",
      content: "Bạn có chắc chắn muốn xóa người dùng này không?",
      centered: true,
      okText: "Xóa",
      okType: "danger",
      cancelText: "Hủy",
      onOk: () => {
        return new Promise((resolve) => {
          deleteMutation.mutate(id, {
            onSuccess: () => {
              message.success("Xóa người dùng thành công!");
              resolve(null);
            },
            onError: (err: any) => {
              message.error(
                getApiErrorMessage(err, "Không thể xóa người dùng"),
              );
              resolve(null);
            },
          });
        });
      },
    });
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const isAdmin = values.role_id === ADMIN_ROLE_ID;

      if (editingUser) {
        const payload: UpdateUserInput = {
          email: values.email.trim(),
          is_admin: isAdmin,
          role_ids: [values.role_id],
        };
        if (values.password?.trim()) {
          payload.password = values.password;
          payload.password_confirm = values.password_confirm ?? "";
        }
        updateMutation.mutate(
          { id: editingUser.id, data: payload },
          {
            onSuccess: () => {
              message.success("Cập nhật người dùng thành công!");
              handleCloseModal();
            },
            onError: (err: any) => {
              message.error(
                getApiErrorMessage(err, "Không thể cập nhật người dùng"),
              );
            },
          },
        );
        return;
      }

      const payload: CreateUserInput = {
        username: values.username.trim(),
        email: values.email.trim(),
        password: values.password ?? "",
        password_confirm: values.password_confirm ?? "",
        is_admin: isAdmin,
        role_ids: [values.role_id],
      };

      createMutation.mutate(payload, {
        onSuccess: () => {
          message.success("Thêm người dùng mới thành công!");
          handleCloseModal();
        },
        onError: (err: any) => {
          message.error(
            getApiErrorMessage(err, "Không thể thêm người dùng mới"),
          );
        },
      });
    } catch {
      // Form validation failed
    }
  };

  const columns = [
    {
      title: "Tên đăng nhập",
      dataIndex: "username",
      key: "username",
      render: (text: string) => (
        <span className="font-semibold text-brand-primary">{text}</span>
      ),
    },
    {
      title: "Email",
      dataIndex: "email",
      key: "email",
      className: "font-medium text-slate-700",
    },
    {
      title: "Vai trò",
      key: "roles",
      render: (_: unknown, record: User) => getRoleTag(record),
    },
    {
      title: "Ngày khởi tạo",
      dataIndex: "created_at",
      key: "created_at",
      render: (val: string) =>
        val ? dayjs(val).format("DD/MM/YYYY HH:mm") : "—",
    },
    {
      title: "Thao tác",
      key: "action",
      width: 260,
      render: (_: unknown, record: User) => {
        const isAdmin = isAdminUser(record);
        return (
          <Space size="small">
            {!isAdmin ? (
              <Button
                variant="outline"
                size="sm"
                icon={<ClusterOutlined className="text-brand-primary" />}
                onClick={() => setStationModalUser(record)}
                title="Phân quyền trạm máy & vị trí"
                className="!h-8 !px-2.5 !rounded-lg text-xs font-semibold text-slate-700 hover:text-brand-primary hover:border-brand-primary"
              >
                Phân trạm
              </Button>
            ) : (
              <Tag color="blue" className="!mr-1 !px-2 !py-0.5 !font-semibold">
                Toàn quyền
              </Tag>
            )}
            <Button
              variant="outline"
              size="sm"
              icon={<EditOutlined />}
              onClick={() => handleOpenEdit(record)}
              className="!h-8 !w-8 !p-0 !rounded-lg text-slate-600 hover:text-brand-primary hover:border-brand-primary"
            />
            <Button
              variant="outline"
              size="sm"
              icon={<DeleteOutlined className="text-red-500" />}
              onClick={() => handleDelete(record.id)}
              className="!h-8 !w-8 !p-0 !rounded-lg text-red-500 hover:text-red-600 hover:border-red-400"
            />
          </Space>
        );
      },
    },
  ];

  const saving = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="space-y-6">
      <Hero
        title="Quản lý Người dùng"
        extra={
          <Button
            onClick={handleOpenCreate}
            icon={<PlusOutlined />}
            className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none !h-10 !rounded-lg font-semibold flex items-center"
          >
            Thêm Người Dùng
          </Button>
        }
      />

      <Card className="shadow-sm border-gray-100/50 rounded-xl overflow-hidden">
        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold [&_.ant-table-row]:hover:bg-slate-50/50 [&_.ant-table-cell]:!text-center"
        />
      </Card>

      <Modal
        title={editingUser ? "Cập nhật Người dùng" : "Thêm Người dùng Mới"}
        open={isModalOpen}
        onCancel={handleCloseModal}
        footer={null}
        destroyOnHidden
        centered
        width={520}
      >
        <Form
          form={form}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="username"
            label="Tên đăng nhập"
            rules={[
              { required: true, message: "Vui lòng nhập tên đăng nhập!" },
              { min: 3, message: "Tối thiểu 3 ký tự" },
            ]}
          >
            <Input placeholder="Ví dụ: operator_cnc01" disabled={!!editingUser} />
          </Form.Item>

          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: "Vui lòng nhập email!" },
              { type: "email", message: "Email không hợp lệ!" },
            ]}
          >
            <Input placeholder="Ví dụ: operator@factory.com" />
          </Form.Item>

          <Form.Item
            name="role_id"
            label="Vai trò & Phân khu"
            rules={[{ required: true, message: "Vui lòng chọn vai trò!" }]}
          >
            <Select
              placeholder="Chọn vai trò"
              options={[
                { value: 2, label: "🛡️ Quản trị viên (Admin / Quản đốc)" },
                { value: 4, label: "⚙️ Operator CNC (Khu Máy CNC)" },
                { value: 3, label: "📦 Operator Cấp Phôi (Khu Nguyên Liệu)" },
                { value: 5, label: "🧼 Operator Tẩy Rửa (Khu Tẩy Rửa)" },
                { value: 1, label: "👷 Operator Vận Hành Chung" },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="Mật khẩu"
            required={!editingUser}
            rules={
              editingUser
                ? [{ min: 8, message: "Tối thiểu 8 ký tự (để trống nếu không đổi)" }]
                : [
                    { required: true, message: "Vui lòng nhập mật khẩu!" },
                    { min: 8, message: "Tối thiểu 8 ký tự" },
                  ]
            }
          >
            <Input.Password placeholder={editingUser ? "Để trống nếu không đổi mật khẩu" : "Tối thiểu 8 ký tự"} />
          </Form.Item>

          <Form.Item
            name="password_confirm"
            label="Nhập lại mật khẩu"
            required={!editingUser}
            dependencies={["password"]}
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const password = getFieldValue("password");
                  if (!password && editingUser) return Promise.resolve();
                  if (!value && password) {
                    return Promise.reject(new Error("Vui lòng nhập lại mật khẩu!"));
                  }
                  if (password === value) return Promise.resolve();
                  return Promise.reject(new Error("Mật khẩu không khớp!"));
                },
              }),
            ]}
          >
            <Input.Password placeholder="Nhập lại mật khẩu" />
          </Form.Item>

          <div className="flex justify-end gap-2 border-t border-gray-100 pt-4 mt-6">
            <Button onClick={handleCloseModal}>Hủy</Button>
            <Button
              loading={saving}
              onClick={handleSubmit}
              className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none font-semibold text-white"
            >
              {editingUser ? "Cập nhật" : "Lưu lại"}
            </Button>
          </div>
        </Form>
      </Modal>

      <StationAssignmentModal
        open={!!stationModalUser}
        onClose={() => setStationModalUser(null)}
        user={stationModalUser}
      />
    </div>
  );
}
