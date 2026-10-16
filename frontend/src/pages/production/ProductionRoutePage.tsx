import React, { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Card,
  Popconfirm,
  message,
  Typography,
  Divider,
  Badge,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  BranchesOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowRightOutlined,
  ToolOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  useActivateProductionRoute,
  useAvailableMachines,
  useCreateProductionRoute,
  useDeleteProductionRoute,
  useProductionRouteDetail,
  useProductionRoutes,
  useUpdateProductionRoute,
} from '@/hooks/useProductionRoute';
import { useItems } from '@/hooks/useItem';
import { useAppStore } from '@/store/useAppStore';
import type {
  ProductionRoute,
  RouteStepInput,
} from '@/types/productionRoute';

const { Title, Text } = Typography;

const MACHINE_TYPES = [
  { label: 'Máy Tiện CNC (CNC Lathe)', value: 'CNC_LATHE' },
  { label: 'Máy Phay CNC (CNC Milling)', value: 'CNC_MILLING' },
  { label: 'Máy Mài Tròn/Phẳng (Grinding)', value: 'CNC_GRINDING' },
  { label: 'Máy Cắt dây / Xung điện (EDM)', value: 'CNC_EDM' },
  { label: 'Trung tâm Gia công 5 trục (5-Axis VMC)', value: '5AXIS_CNC' },
];

export default function ProductionRoutePage() {
  const selectedWarehouseId = useAppStore((state) => state.selectedWarehouseId) || 1;
  const [selectedItemId, setSelectedItemId] = useState<number | undefined>(undefined);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<ProductionRoute | null>(null);

  const [form] = Form.useForm();

  // Queries
  const { data: routes = [], isLoading: isLoadingRoutes } = useProductionRoutes({
    item_id: selectedItemId,
  });
  const { data: machines = [] } = useAvailableMachines();
  const { data: itemsData } = useItems({
    warehouse_id: selectedWarehouseId,
    page: 1,
    page_size: 100,
  });
  const items = itemsData?.items || [];

  // Mutations
  const createMutation = useCreateProductionRoute();
  const updateMutation = useUpdateProductionRoute();
  const activateMutation = useActivateProductionRoute();
  const deleteMutation = useDeleteProductionRoute();

  // Route Detail for editing
  const { data: detailData } = useProductionRouteDetail(editingRoute?.id);

  // Open modal for Create with realistic mechanical engineering default steps
  const handleOpenCreate = () => {
    setEditingRoute(null);
    form.resetFields();
    form.setFieldsValue({
      version: 1,
      is_active: true,
      steps: [
        {
          step_number: 1,
          stage_level: 1,
          operation_code: 'OP10',
          step_name: 'Tiện thô mặt đầu & tiện bậc ngoài',
          machine_type: 'CNC_LATHE',
          cycle_time_minutes: 12,
          program_number: 'O1001.NC',
          allowed_machines: ['CNC-01', 'CNC-02'],
          is_final_cnc_step: false,
        },
        {
          step_number: 2,
          stage_level: 2,
          operation_code: 'OP20',
          step_name: 'Phay rãnh then & khoan 4 lỗ taro M8',
          machine_type: 'CNC_MILLING',
          cycle_time_minutes: 18,
          program_number: 'O2001.NC',
          allowed_machines: ['CNC-03'],
          is_final_cnc_step: false,
        },
        {
          step_number: 3,
          stage_level: 3,
          operation_code: 'OP30',
          step_name: 'Tiện tinh & mài bóng đạt Ra 0.8',
          machine_type: 'CNC_LATHE',
          cycle_time_minutes: 15,
          program_number: 'O3001.NC',
          allowed_machines: ['CNC-04'],
          is_final_cnc_step: true,
        },
      ],
    });
    setIsModalOpen(true);
  };

  // Open modal for Edit
  const handleOpenEdit = (record: ProductionRoute) => {
    setEditingRoute(record);
    setIsModalOpen(true);
  };

  // Populate form when detail is loaded
  React.useEffect(() => {
    if (editingRoute && detailData && isModalOpen) {
      form.setFieldsValue({
        route_code: detailData.route_code,
        route_name: detailData.route_name,
        item_id: detailData.item_id,
        version: detailData.version,
        is_active: detailData.is_active,
        steps: detailData.steps?.map((s, idx) => ({
          step_number: s.step_number || idx + 1,
          stage_level: s.stage_level || idx + 1,
          operation_code: s.operation_code || `OP${(idx + 1) * 10}`,
          step_name: s.step_name,
          machine_type: s.machine_type || 'CNC_MILLING',
          cycle_time_minutes: s.cycle_time_minutes || 15,
          program_number: s.program_number || '',
          allowed_machines: s.allowed_machines || [],
          is_final_cnc_step: !!s.is_final_cnc_step,
        })) || [],
      });
    }
  }, [editingRoute, detailData, isModalOpen, form]);

  // Handle Form Submit
  const handleFormSubmit = async () => {
    try {
      const values = await form.validateFields();
      const stepsPayload: RouteStepInput[] = (values.steps || []).map(
        (s: any, idx: number) => ({
          step_number: idx + 1,
          stage_level: Number(s.stage_level),
          operation_code: (s.operation_code || `OP${(idx + 1) * 10}`).trim().toUpperCase(),
          step_name: s.step_name.trim(),
          machine_type: s.machine_type || 'CNC_MILLING',
          cycle_time_minutes: Number(s.cycle_time_minutes) || 15,
          program_number: s.program_number?.trim() || undefined,
          allowed_machines: s.allowed_machines || [],
          is_final_cnc_step: !!s.is_final_cnc_step,
        }),
      );

      if (editingRoute) {
        await updateMutation.mutateAsync({
          routeId: editingRoute.id,
          payload: {
            route_name: values.route_name,
            version: values.version,
            is_active: values.is_active,
            steps: stepsPayload,
          },
        });
        message.success('Cập nhật quy trình gia công thành công!');
      } else {
        await createMutation.mutateAsync({
          route_code: values.route_code.trim().toUpperCase(),
          route_name: values.route_name.trim(),
          item_id: values.item_id,
          version: values.version || 1,
          is_active: values.is_active ?? true,
          steps: stepsPayload,
        });
        message.success('Tạo mới quy trình công nghệ thành công!');
      }
      setIsModalOpen(false);
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Thao tác thất bại');
    }
  };

  // Handle Activate
  const handleActivate = async (id: number) => {
    try {
      await activateMutation.mutateAsync(id);
      message.success('Đã kích hoạt quy trình công nghệ thành công!');
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Kích hoạt thất bại');
    }
  };

  // Handle Delete
  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('Đã xóa quy trình!');
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Xóa thất bại');
    }
  };

  const columns: ColumnsType<ProductionRoute> = [
    {
      title: 'Mã quy trình',
      dataIndex: 'route_code',
      key: 'route_code',
      render: (code: string) => (
        <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded border border-slate-200">
          {code}
        </span>
      ),
    },
    {
      title: 'Tên quy trình',
      dataIndex: 'route_name',
      key: 'route_name',
      render: (name: string, record) => (
        <div>
          <div className="font-semibold text-slate-900">{name}</div>
          <div className="text-xs text-slate-400">Phiên bản v{record.version}</div>
        </div>
      ),
    },
    {
      title: 'Model chi tiết',
      dataIndex: 'item',
      key: 'item',
      render: (item: any) => (
        <div>
          {item ? (
            <Tag color="orange" className="font-semibold text-xs">
              {item.sku} - {item.name}
            </Tag>
          ) : (
            <Tag color="default">N/A</Tag>
          )}
        </div>
      ),
    },
    {
      title: 'Công đoạn',
      dataIndex: 'step_count',
      key: 'step_count',
      align: 'center',
      render: (count: number) => (
        <Badge
          count={`${count} nguyên công`}
          style={{ backgroundColor: '#0284c7', fontWeight: 600 }}
        />
      ),
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag
          icon={isActive ? <CheckCircleOutlined /> : undefined}
          color={isActive ? 'success' : 'default'}
          className="font-medium px-2 py-0.5"
        >
          {isActive ? 'ĐANG ÁP DỤNG' : 'TẠM TẮT'}
        </Tag>
      ),
    },
    {
      title: 'Thao tác',
      key: 'actions',
      align: 'right',
      render: (_, record) => (
        <Space size="middle">
          {!record.is_active && (
            <Button
              size="small"
              type="link"
              className="text-emerald-600 font-semibold p-0"
              onClick={() => handleActivate(record.id)}
            >
              Kích hoạt
            </Button>
          )}
          <Button
            size="small"
            type="text"
            icon={<EditOutlined className="text-blue-600" />}
            onClick={() => handleOpenEdit(record)}
          >
            Sửa
          </Button>
          <Popconfirm
            title="Xác nhận xóa quy trình"
            description="Bạn có chắc chắn muốn xóa quy trình này và tất cả các công đoạn bên trong?"
            onConfirm={() => handleDelete(record.id)}
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
          >
            <Button
              size="small"
              type="text"
              danger
              icon={<DeleteOutlined />}
            >
              Xóa
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="p-6 bg-slate-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-6 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-500 flex items-center justify-center text-white shadow-lg shadow-orange-500/20">
              <BranchesOutlined className="text-xl" />
            </div>
            <div>
              <Title level={3} className="!mb-0 text-slate-800">
                Quy trình Công nghệ Gia công CNC (Routing Sheet)
              </Title>
              <Text type="secondary" className="text-sm">
                Thiết lập chuỗi nguyên công OP10, OP20, OP30, máy CNC thực hiện và thời gian chu kỳ điều phối AMR
              </Text>
            </div>
          </div>
        </div>

        <div className="mt-4 md:mt-0 flex items-center gap-3">
          <Select
            allowClear
            placeholder="Lọc theo Model chi tiết"
            className="w-56"
            value={selectedItemId}
            onChange={(val) => setSelectedItemId(val)}
          >
            {items.map((it: any) => (
              <Select.Option key={it.id} value={it.id}>
                {it.sku} - {it.name}
              </Select.Option>
            ))}
          </Select>

          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleOpenCreate}
            className="bg-amber-600 hover:bg-amber-500 font-semibold shadow-sm h-10 px-5"
          >
            Thêm Quy trình mới
          </Button>
        </div>
      </div>

      {/* Main Table */}
      <Card className="shadow-sm border-slate-200 rounded-xl">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={routes}
          loading={isLoadingRoutes}
          pagination={{ pageSize: 10 }}
          expandable={{
            expandedRowRender: (record) => <RouteDetailTimeline routeId={record.id} />,
            rowExpandable: () => true,
          }}
        />
      </Card>

      {/* Create / Edit Modal */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-slate-800 text-lg font-bold">
            <ToolOutlined className="text-amber-500" />
            {editingRoute ? 'Chỉnh sửa Quy trình Công nghệ' : 'Tạo mới Quy trình Công nghệ'}
          </div>
        }
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onOk={handleFormSubmit}
        width={850}
        okText={editingRoute ? 'Lưu thay đổi' : 'Tạo quy trình'}
        cancelText="Hủy"
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Form.Item
              name="item_id"
              label="Model sản phẩm chi tiết"
              rules={[{ required: true, message: 'Vui lòng chọn Model sản phẩm' }]}
            >
              <Select
                placeholder="Chọn Model sản phẩm"
                disabled={!!editingRoute}
                className="w-full"
              >
                {items.map((it: any) => (
                  <Select.Option key={it.id} value={it.id}>
                    {it.sku} - {it.name}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="route_code"
              label="Mã quy trình (Routing Code)"
              rules={[{ required: true, message: 'Vui lòng nhập mã quy trình' }]}
            >
              <Input
                placeholder="Ví dụ: RT-MDL01-V1"
                disabled={!!editingRoute}
                className="font-mono uppercase"
              />
            </Form.Item>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Form.Item
              name="route_name"
              label="Tên quy trình gia công"
              className="md:col-span-2"
              rules={[{ required: true, message: 'Vui lòng nhập tên quy trình' }]}
            >
              <Input placeholder="Ví dụ: Quy trình tiện phay chi tiết Trục Rotor v1" />
            </Form.Item>

            <Form.Item name="version" label="Phiên bản">
              <Input type="number" min={1} placeholder="1" />
            </Form.Item>
          </div>

          <Form.Item
            name="is_active"
            valuePropName="checked"
            label="Kích hoạt áp dụng"
            extra="Khi bật kích hoạt, quy trình này sẽ trở thành quy trình mặc định để hệ thống điều phối xe AMR cấp phôi và trung chuyển."
          >
            <Switch checkedChildren="KÍCH HOẠT" unCheckedChildren="TẮT" />
          </Form.Item>

          <Divider orientation="left" className="!text-sm !font-bold text-slate-700">
            DANH SÁCH CÁC NGUYÊN CÔNG GIA CÔNG (OPERATIONS: OP10, OP20...)
          </Divider>

          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <div className="space-y-4">
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    className="bg-slate-50/80 border-slate-200 rounded-lg shadow-sm"
                    title={
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                        <span className="flex items-center gap-2">
                          <Tag color="red" className="font-mono font-bold">
                            BƯỚC {index + 1}
                          </Tag>
                          <span>CÔNG ĐOẠN LEVEL {index + 1}</span>
                        </span>
                        {fields.length > 1 && (
                          <Button
                            type="text"
                            danger
                            size="small"
                            icon={<DeleteOutlined />}
                            onClick={() => remove(field.name)}
                          >
                            Xóa bước
                          </Button>
                        )}
                      </div>
                    }
                  >
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                      <Form.Item
                        {...field}
                        name={[field.name, 'operation_code']}
                        label="Mã OP"
                        rules={[{ required: true, message: 'Nhập mã OP' }]}
                        className="!mb-2"
                      >
                        <Input placeholder="OP10" className="font-mono uppercase font-bold" />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'step_name']}
                        label="Tên nguyên công"
                        rules={[{ required: true, message: 'Nhập tên nguyên công' }]}
                        className="md:col-span-2 !mb-2"
                      >
                        <Input placeholder="Ví dụ: Tiện thô mặt đầu & tiện bậc" />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'stage_level']}
                        label="Stage Level"
                        rules={[{ required: true, message: 'Chọn level' }]}
                        className="!mb-2"
                      >
                        <Select placeholder="Chọn level">
                          <Select.Option value={1}>Stage Level 1</Select.Option>
                          <Select.Option value={2}>Stage Level 2</Select.Option>
                          <Select.Option value={3}>Stage Level 3</Select.Option>
                          <Select.Option value={4}>Stage Level 4</Select.Option>
                          <Select.Option value={5}>Stage Level 5</Select.Option>
                        </Select>
                      </Form.Item>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-1">
                      <Form.Item
                        {...field}
                        name={[field.name, 'machine_type']}
                        label="Loại máy yêu cầu"
                        className="!mb-2"
                      >
                        <Select options={MACHINE_TYPES} placeholder="Chọn loại máy" />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'cycle_time_minutes']}
                        label="Thời gian chu kỳ (phút/xe)"
                        className="!mb-2"
                      >
                        <InputNumber min={1} max={999} className="w-full" prefix={<ClockCircleOutlined />} />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'program_number']}
                        label="Mã chương trình CNC"
                        className="!mb-2"
                      >
                        <Input placeholder="O1001.NC" className="font-mono" prefix={<CodeOutlined />} />
                      </Form.Item>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1 pt-2 border-t border-slate-100">
                      <Form.Item
                        {...field}
                        name={[field.name, 'allowed_machines']}
                        label="Máy CNC được phép thực hiện (Gán theo Layout xưởng)"
                        rules={[{ required: true, message: 'Chọn ít nhất 1 máy' }]}
                        className="!mb-2"
                      >
                        <Select
                          mode="multiple"
                          placeholder="Chọn các máy CNC thực hiện nguyên công này"
                          options={machines.map((m) => ({
                            label: `${m.machine_code} (${m.location_count} vị trí đỗ: ${m.positions.join(', ')})`,
                            value: m.machine_code,
                          }))}
                        />
                      </Form.Item>

                      <Form.Item
                        {...field}
                        name={[field.name, 'is_final_cnc_step']}
                        valuePropName="checked"
                        label="Hành động khi hoàn thành"
                        className="!mb-2"
                      >
                        <Switch
                          checkedChildren="LÀ BƯỚC CUỐI (TỰ ĐIỀU AMR SANG TẨY RỬA)"
                          unCheckedChildren="Chuyển sang công đoạn tiếp theo"
                        />
                      </Form.Item>
                    </div>
                  </Card>
                ))}

                <Button
                  type="dashed"
                  onClick={() =>
                    add({
                      step_number: fields.length + 1,
                      stage_level: fields.length + 1,
                      operation_code: `OP${(fields.length + 1) * 10}`,
                      step_name: `Nguyên công ${fields.length + 1}`,
                      machine_type: 'CNC_MILLING',
                      cycle_time_minutes: 15,
                      program_number: '',
                      allowed_machines: [],
                      is_final_cnc_step: false,
                    })
                  }
                  block
                  icon={<PlusOutlined />}
                  className="h-10 text-amber-600 border-amber-300 hover:border-amber-500 font-medium"
                >
                  + Thêm nguyên công gia công (OP)
                </Button>
              </div>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
}

// Sub-component rendering the visual timeline of steps
function RouteDetailTimeline({ routeId }: { routeId: number }) {
  const { data, isLoading } = useProductionRouteDetail(routeId);

  if (isLoading) {
    return <div className="p-4 text-center text-slate-400">Đang tải chi tiết các bước...</div>;
  }

  const steps = data?.steps || [];

  if (steps.length === 0) {
    return (
      <div className="p-4 text-center text-slate-400 bg-slate-50 rounded">
        Chưa có bước công nghệ nào được thiết lập.
      </div>
    );
  }

  return (
    <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200">
      <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
        Sơ đồ luồng công nghệ & Chu kỳ gia công KUKA AMR:
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {/* Nguyên liệu xuất phát */}
        <div className="bg-white p-3 rounded-lg border border-slate-300 shadow-sm flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-slate-100 flex items-center justify-center font-bold text-xs text-slate-600">
            L0
          </div>
          <div>
            <div className="font-semibold text-xs text-slate-800">Kho Nguyên Liệu</div>
            <div className="text-[11px] text-slate-400">Phôi thô đúc/cắt (FIFO)</div>
          </div>
        </div>

        <ArrowRightOutlined className="text-slate-400" />

        {/* Các bước CNC */}
        {steps.map((s, idx) => (
          <React.Fragment key={s.id || idx}>
            <div
              className={`p-3 rounded-lg border shadow-sm ${
                s.is_final_cnc_step
                  ? 'bg-amber-50/90 border-amber-300'
                  : 'bg-white border-blue-200'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <Tag color="volcano" className="!mr-0 font-bold font-mono">
                  {s.operation_code || `OP${s.step_number * 10}`}
                </Tag>
                <Tag color={s.is_final_cnc_step ? 'orange' : 'blue'} className="!mr-0 font-medium">
                  Level {s.stage_level}
                </Tag>
                <span className="font-semibold text-xs text-slate-800">{s.step_name}</span>
              </div>

              <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                {s.machine_type && (
                  <Tag color="purple" className="text-[10px] !mr-0">
                    {s.machine_type.replace('CNC_', '')}
                  </Tag>
                )}
                {s.cycle_time_minutes && (
                  <Tag color="geekblue" className="text-[10px] !mr-0">
                    ⏱ {s.cycle_time_minutes}p
                  </Tag>
                )}
                {s.program_number && (
                  <Tag color="default" className="text-[10px] !mr-0 font-mono">
                    {s.program_number}
                  </Tag>
                )}
                <span className="text-[11px] text-slate-400 ml-1">Máy:</span>
                {(s.allowed_machines || []).map((m) => (
                  <Tag key={m} color="cyan" className="text-[10px] !mr-0.5 font-mono">
                    {m}
                  </Tag>
                ))}
                {s.is_final_cnc_step && (
                  <Tag color="red" className="text-[10px] !mr-0 font-bold">
                    🚀 CHUYỂN TẨY RỬA
                  </Tag>
                )}
              </div>
            </div>

            {idx < steps.length - 1 ? (
              <ArrowRightOutlined className="text-slate-400" />
            ) : null}
          </React.Fragment>
        ))}

        <ArrowRightOutlined className="text-slate-400" />

        {/* Tẩy Rửa */}
        <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-300 shadow-sm flex items-center gap-2">
          <div className="w-8 h-8 rounded bg-emerald-100 flex items-center justify-center font-bold text-xs text-emerald-700">
            WASH
          </div>
          <div>
            <div className="font-semibold text-xs text-emerald-900">Khu Tẩy Rửa</div>
            <div className="text-[11px] text-emerald-600">Slot 1 - 4 (Giải phóng xe)</div>
          </div>
        </div>
      </div>
    </div>
  );
}
