import { useMemo, useState } from "react";
import type { AxiosError } from "axios";
import type { ApiErrorResponse } from "@/types/apiError";
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
  cn,
} from "@/components/ui";
import { Checkbox, Steps, Tag } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, ClusterOutlined } from "@ant-design/icons";
import { getApiErrorMessage } from "@/utils/apiErrorMessage";
import StationAssignmentModal from "@/pages/components/StationAssignmentModal";
import {
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
} from "@/hooks/useAuth";
import { useWarehouses } from "@/hooks/useWarehouse";
import {
  MODULE_OPTIONS,
  MODULE_ROLE_NAMES,
  ROLE_OPTIONS,
  type CreateUserInput,
  type UpdateUserInput,
  type User,
  type UserModule,
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

const ADMIN_ROLE_ID = ROLE_OPTIONS.find((r) => r.name === "admin")?.id ?? 1;
const OPERATOR_ROLE_ID =
  ROLE_OPTIONS.find((r) => r.name === "operator")?.id ?? 2;

const STEP_ITEMS = [
  { title: "Thông tin" },
  { title: "Kho" },
  { title: "Chức năng" },
];

function modulesFromRoles(user: User): UserModule[] {
  const names = new Set(user.roles?.map((r) => r.name) ?? []);
  return MODULE_ROLE_NAMES.filter((m) => names.has(m));
}

function isAdminUser(user: User | null): boolean {
  return !!user?.roles?.some((r) => r.name === "admin");
}

export default function UserSettingPage() {
  const { data: users, isLoading, error } = useUser();
  const { data: warehouses = [] } = useWarehouses();
  const createMutation = useCreateUser();
  const updateMutation = useUpdateUser();
  const deleteMutation = useDeleteUser();

  const [form] = Form.useForm<UserFormValues>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [stationModalUser, setStationModalUser] = useState<User | null>(null);
  const [step, setStep] = useState(0);
  const [selectedWarehouseIds, setSelectedWarehouseIds] = useState<number[]>(
    [],
  );
  const [selectedModules, setSelectedModules] = useState<UserModule[]>([]);

  const watchedRoleId = Form.useWatch("role_id", form);
  const isAdminFlow = watchedRoleId === ADMIN_ROLE_ID;

  const allWarehouseIds = useMemo(
    () => warehouses.map((w) => w.id),
    [warehouses],
  );

  const resetWizard = () => {
    setStep(0);
    setSelectedWarehouseIds([]);
    setSelectedModules([]);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingUser(null);
    form.resetFields();
    resetWizard();
  };

  const handleOpenCreate = () => {
    setEditingUser(null);
    form.resetFields();
    form.setFieldsValue({ role_id: ADMIN_ROLE_ID });
    resetWizard();
    setIsModalOpen(true);
  };

  const handleOpenEdit = (record: User) => {
    setEditingUser(record);
    const admin = isAdminUser(record);
    form.setFieldsValue({
      username: record.username,
      email: record.email,
      role_id: admin ? ADMIN_ROLE_ID : OPERATOR_ROLE_ID,
      password: undefined,
      password_confirm: undefined,
    });
    setSelectedWarehouseIds(record.warehouses?.map((w) => w.id) ?? []);
    setSelectedModules(modulesFromRoles(record));
    setStep(0);
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

  const validateStep1 = async () => {
    const fields: (keyof UserFormValues)[] = [
      "username",
      "email",
      "role_id",
      "password",
      "password_confirm",
    ];
    await form.validateFields(fields);
  };

  const handleNext = async () => {
    if (step === 0) {
      await validateStep1();
      if (isAdminFlow) return;
      setStep(1);
      return;
    }
    if (step === 1) {
      if (selectedWarehouseIds.length === 0) {
        message.warning("Vui lòng chọn ít nhất một kho!");
        return;
      }
      setStep(2);
    }
  };

  const handleBack = () => {
    setStep((s) => Math.max(0, s - 1));
  };

  const submitPayload = (values: UserFormValues) => {
    const isAdmin = values.role_id === ADMIN_ROLE_ID;

    if (editingUser) {
      const payload: UpdateUserInput = {
        email: values.email.trim(),
        is_admin: isAdmin,
        role_ids: isAdmin ? [ADMIN_ROLE_ID] : [OPERATOR_ROLE_ID],
      };
      if (!isAdmin) {
        payload.warehouse_ids = selectedWarehouseIds;
        payload.modules = selectedModules;
      } else {
        payload.warehouse_ids = [];
        payload.modules = [];
      }
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
      role_ids: isAdmin ? [ADMIN_ROLE_ID] : [OPERATOR_ROLE_ID],
      warehouse_ids: isAdmin ? [] : selectedWarehouseIds,
      modules: isAdmin ? [] : selectedModules,
    };

    createMutation.mutate(payload, {
      onSuccess: () => {
        message.success("Thêm người dùng thành công!");
        handleCloseModal();
      },
      onError: (err: any) => {
        message.error(
          getApiErrorMessage(err, "Không thể thêm người dùng mới"),
        );
      },
    });
  };

  const handleSubmit = async () => {
    try {
      await validateStep1();
    } catch {
      setStep(0);
      return;
    }

    const values = form.getFieldsValue(true) as UserFormValues;
    const isAdmin = values.role_id === ADMIN_ROLE_ID;

    if (!isAdmin) {
      if (selectedWarehouseIds.length === 0) {
        message.warning("Vui lòng chọn ít nhất một kho!");
        setStep(1);
        return;
      }
      if (selectedModules.length === 0) {
        message.warning("Vui lòng chọn ít nhất một chức năng!");
        setStep(2);
        return;
      }
    }

    submitPayload(values);
  };

  const allWarehousesSelected =
    allWarehouseIds.length > 0 &&
    allWarehouseIds.every((id) => selectedWarehouseIds.includes(id));

  const allModulesSelected =
    MODULE_OPTIONS.length > 0 &&
    MODULE_OPTIONS.every((m) => selectedModules.includes(m.key));

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
      render: (_: unknown, record: User) =>
        record.roles?.map((r) => r.name).join(", ") || "—",
    },
    {
      title: "Kho",
      key: "warehouses",
      render: (_: unknown, record: User) =>
        record.warehouses?.map((w) => w.code).join(", ") || "—",
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
      width: 240,
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
              variant="edit"
              icon={<EditOutlined className="text-brand-primary" />}
              onClick={() => handleOpenEdit(record)}
              title="Sửa thông tin"
            />
            <Button
              variant="dangerText"
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(record.id)}
              className="hover:bg-red-50 rounded-lg"
              title="Xóa người dùng"
            />
          </Space>
        );
      },
    },
  ];

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <span className="text-brand-primary/70 font-medium">
          Đang tải danh sách người dùng...
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

  const showSteps = !isAdminFlow;
  const isLastStep = isAdminFlow || step === 2;
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
        width="60vw"
        className="!max-w-[60vw] [&_.ant-modal-content]:!h-[60vh] [&_.ant-modal-content]:!flex [&_.ant-modal-content]:!flex-col [&_.ant-modal-body]:!flex-1 [&_.ant-modal-body]:!overflow-hidden [&_.ant-modal-body]:!flex [&_.ant-modal-body]:!flex-col"
      >
        {showSteps && (
          <Steps
            size="small"
            current={step}
            items={STEP_ITEMS}
            className="mt-1 mb-4 shrink-0"
          />
        )}

        <Form
          form={form}
          layout="vertical"
          className={cn(
            "flex min-h-0 flex-1 flex-col",
            !showSteps && "mt-2",
          )}
        >
          <div className="min-h-0 flex-1 overflow-y-auto pr-1">
            <div className={cn(step !== 0 && "hidden")}>
              <Form.Item
                name="username"
                label="Tên đăng nhập"
                rules={[
                  { required: true, message: "Vui lòng nhập tên đăng nhập!" },
                  { min: 3, message: "Tối thiểu 3 ký tự" },
                ]}
              >
                <Input placeholder="Ví dụ: admin" disabled={!!editingUser} />
              </Form.Item>

              <Form.Item
                name="email"
                label="Email"
                rules={[
                  { required: true, message: "Vui lòng nhập email!" },
                  { type: "email", message: "Email không hợp lệ!" },
                ]}
              >
                <Input placeholder="Ví dụ: example@example.com" />
              </Form.Item>

              <Form.Item
                name="role_id"
                label="Vai trò"
                rules={[{ required: true, message: "Vui lòng chọn vai trò!" }]}
              >
                <Select
                  placeholder="Chọn vai trò"
                  options={[
                    { value: 2, label: "Admin (Quản trị viên)" },
                    { value: 3, label: "Operator Cấp Phôi (Khu Nguyên Liệu)" },
                    { value: 4, label: "Operator CNC (Khu Máy CNC)" },
                    { value: 5, label: "Operator Tẩy Rửa (Khu Tẩy Rửa & Xe Rỗng)" },
                    { value: 1, label: "Operator Vận Hành Chung" },
                  ]}
                  onChange={(value) => {
                    if (value === 2) {
                      setStep(0);
                    }
                  }}
                />
              </Form.Item>

              <Form.Item
                name="password"
                label="Mật khẩu"
                required={!editingUser}
                rules={
                  editingUser
                    ? [{ min: 8, message: "Tối thiểu 8 ký tự" }]
                    : [
                      { required: true, message: "Vui lòng nhập mật khẩu!" },
                      { min: 8, message: "Tối thiểu 8 ký tự" },
                    ]
                }
              >
                <Input.Password placeholder="Tối thiểu 8 ký tự" />
              </Form.Item>

              <Form.Item
                name="password_confirm"
                label="Nhập lại mật khẩu"
                required={!editingUser}
                dependencies={["password"]}
                rules={
                  editingUser
                    ? [
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          const password = getFieldValue("password");
                          if (!password) return Promise.resolve();
                          if (!value) {
                            return Promise.reject(
                              new Error("Vui lòng nhập lại mật khẩu!"),
                            );
                          }
                          if (password === value) return Promise.resolve();
                          return Promise.reject(
                            new Error("Mật khẩu không khớp!"),
                          );
                        },
                      }),
                    ]
                    : [
                      {
                        required: true,
                        message: "Vui lòng nhập lại mật khẩu!",
                      },
                      ({ getFieldValue }) => ({
                        validator(_, value) {
                          if (!value || getFieldValue("password") === value) {
                            return Promise.resolve();
                          }
                          return Promise.reject(
                            new Error("Mật khẩu không khớp!"),
                          );
                        },
                      }),
                    ]
                }
              >
                <Input.Password placeholder="Nhập lại mật khẩu" />
              </Form.Item>
            </div>

            <div className={cn(step !== 1 && "hidden")}>
              <div className="mb-3 space-y-2">
                <p className="text-sm text-slate-600">
                  Chọn kho mà người dùng được phép truy cập
                </p>
                <Checkbox
                  checked={allWarehousesSelected}
                  indeterminate={
                    selectedWarehouseIds.length > 0 && !allWarehousesSelected
                  }
                  onChange={(e) => {
                    setSelectedWarehouseIds(
                      e.target.checked ? allWarehouseIds : [],
                    );
                  }}
                >
                  Chọn tất cả
                </Checkbox>
              </div>
              <Checkbox.Group
                className="flex w-full flex-col gap-3"
                value={selectedWarehouseIds}
                onChange={(vals) =>
                  setSelectedWarehouseIds(vals.map((v) => Number(v)))
                }
                options={warehouses.map((w) => ({
                  value: w.id,
                  label: w.name ? `${w.code} — ${w.name}` : w.code,
                }))}
              />
              {warehouses.length === 0 && (
                <p className="text-sm text-slate-400">Chưa có kho nào.</p>
              )}
            </div>

            <div className={cn(step !== 2 && "hidden")}>
              <div className="mb-3 space-y-2">
                <p className="text-sm text-slate-600">
                  Chọn chức năng được phép sử dụng
                </p>
                <Checkbox
                  checked={allModulesSelected}
                  indeterminate={
                    selectedModules.length > 0 && !allModulesSelected
                  }
                  onChange={(e) => {
                    setSelectedModules(
                      e.target.checked
                        ? MODULE_OPTIONS.map((m) => m.key)
                        : [],
                    );
                  }}
                >
                  Chọn tất cả
                </Checkbox>
              </div>
              <Checkbox.Group
                className="flex w-full flex-col gap-3"
                value={selectedModules}
                onChange={(vals) => setSelectedModules(vals as UserModule[])}
                options={MODULE_OPTIONS.map((m) => ({
                  value: m.key,
                  label: m.label,
                }))}
              />
            </div>
          </div>

          <Form.Item className="mb-0 mt-4 shrink-0 flex justify-end border-t border-gray-100 pt-4">
            <Space>
              {step > 0 && !isAdminFlow && (
                <Button onClick={handleBack}>Quay lại</Button>
              )}
              <Button onClick={handleCloseModal}>Hủy</Button>
              {!isLastStep ? (
                <Button
                  onClick={() => {
                    void handleNext().catch(() => undefined);
                  }}
                  className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none"
                >
                  Tiếp theo
                </Button>
              ) : (
                <Button
                  loading={saving}
                  onClick={() => {
                    void handleSubmit();
                  }}
                  className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none"
                >
                  {editingUser ? "Cập nhật" : "Lưu lại"}
                </Button>
              )}
            </Space>
          </Form.Item>
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
