import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Button,
  Modal,
  Input,
  Select,
  message,
  Table,
} from '@/components/ui';
import { Tag, Switch, Tooltip, Alert } from 'antd';
import {
  ReloadOutlined,
  StopOutlined,
  SearchOutlined,
  InboxOutlined,
  ClockCircleOutlined,
  CarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  SwapRightOutlined,
  UserOutlined,
} from '@ant-design/icons';
import Hero from '@/components/shared/Hero';
import {
  getProductionRequestsApi,
  cancelProductionRequestApi,
  type TransportRequestManagementItem,
} from '@/api/requestManagement';

const REQUEST_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  PULL_RAW_MATERIAL: { label: 'Gọi phôi thô vào CNC', color: 'blue' },
  CALL_MATERIAL: { label: 'Gọi phôi vào CNC', color: 'blue' },
  MOVE_BETWEEN_CNC: { label: 'Chuyển giữa máy CNC', color: 'purple' },
  MOVE_TO_WASH: { label: 'Chuyển sang Tẩy Rửa', color: 'cyan' },
  SEND_TO_WASH: { label: 'Chuyển sang Tẩy Rửa', color: 'cyan' },
  RETURN_EMPTY_CART: { label: 'Trả xe rỗng về bãi', color: 'default' },
};

const AREA_LABELS: Record<string, { label: string; color: string }> = {
  RAW_MATERIAL: { label: 'Khu Nguyên Liệu', color: 'blue' },
  CNC_SLOT: { label: 'Máy CNC', color: 'purple' },
  WASHING_SLOT: { label: 'Khu Tẩy Rửa', color: 'cyan' },
  EMPTY_CART_BUFFER: { label: 'Bãi Xe Trống', color: 'default' },
};

const STATUS_META: Record<
  string,
  { label: string; color: string; icon?: React.ReactNode }
> = {
  pending: {
    label: 'Đang khởi tạo',
    color: 'processing',
    icon: <ClockCircleOutlined />,
  },
  queued_for_cart: {
    label: 'Chờ xe phôi (WAITING_CART)',
    color: 'warning',
    icon: <ClockCircleOutlined />,
  },
  queued_for_slot: {
    label: 'Chờ ô trống (WAITING_SLOT)',
    color: 'gold',
    icon: <ClockCircleOutlined />,
  },
  in_progress: {
    label: 'Đang điều xe AMR',
    color: 'processing',
    icon: <CarOutlined />,
  },
  completed: {
    label: 'Đã hoàn thành',
    color: 'success',
    icon: <CheckCircleOutlined />,
  },
  cancelled: {
    label: 'Đã hủy',
    color: 'default',
    icon: <CloseCircleOutlined />,
  },
  failed: {
    label: 'Thất bại',
    color: 'error',
    icon: <ExclamationCircleOutlined />,
  },
};

export default function RequestManagementPage() {
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [includeHistory, setIncludeHistory] = useState(false);

  const [cancellingReq, setCancellingReq] =
    useState<TransportRequestManagementItem | null>(null);
  const [cancelErrorMsg, setCancelErrorMsg] = useState<string | null>(null);

  const {
    data: requests = [],
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['production-requests', { includeHistory }],
    queryFn: () =>
      getProductionRequestsApi({ include_history: includeHistory }),
    refetchInterval: 5000,
  });

  const filteredRequests = useMemo(() => {
    return requests.filter((r) => {
      if (statusFilter !== 'ALL' && r.status !== statusFilter) {
        return false;
      }
      if (typeFilter !== 'ALL' && r.request_type !== typeFilter) {
        return false;
      }
      if (searchText.trim()) {
        const kw = searchText.trim().toLowerCase();
        const haystacks = [
          r.request_code,
          r.container_code,
          r.mission_code,
          r.item_sku,
          r.item_name,
          r.source_location_name,
          r.source_location_code,
          r.source_location_label,
          r.source_machine_code,
          r.destination_location_name,
          r.destination_location_code,
          r.destination_location_label,
          r.destination_machine_code,
          r.created_by_username,
        ];
        const matched = haystacks.some((h) =>
          (h || '').toLowerCase().includes(kw),
        );
        if (!matched) return false;
      }
      return true;
    });
  }, [requests, statusFilter, typeFilter, searchText]);

  const stats = useMemo(() => {
    const active = requests.filter((r) => r.can_cancel);
    return {
      totalActive: active.length,
      waitingCart: active.filter((r) => r.status === 'queued_for_cart').length,
      waitingSlot: active.filter((r) => r.status === 'queued_for_slot').length,
      inProgress: active.filter((r) => r.status === 'in_progress').length,
    };
  }, [requests]);

  const cancelMutation = useMutation({
    mutationFn: (requestId: number) => cancelProductionRequestApi(requestId),
    onSuccess: (res) => {
      message.success(res.message || 'Đã hủy yêu cầu thành công');
      setCancellingReq(null);
      setCancelErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ['production-requests'] });
      queryClient.invalidateQueries({ queryKey: ['production-racks'] });
    },
    onError: (err: any) => {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Không thể hủy yêu cầu vận chuyển.';
      setCancelErrorMsg(detail);
      message.error(detail);
    },
  });

  const renderStationBlock = (
    locName: string | null,
    locCode: string | null,
    locLabel: string | null,
    locType: string | null,
    machineCode: string | null,
    fallbackText: string,
  ) => {
    if (!locName && !locCode) {
      return <span className="text-xs text-slate-400 italic">{fallbackText}</span>;
    }
    const areaInfo = locType ? AREA_LABELS[locType] : null;
    return (
      <div className="flex flex-col gap-0.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          {machineCode && (
            <Tag color="geekblue" className="m-0 font-mono text-[11px] font-bold">
              {machineCode}
            </Tag>
          )}
          <span className="font-semibold text-slate-800 text-xs">
            {locName || locCode}
          </span>
          {areaInfo && (
            <Tag color={areaInfo.color} className="m-0 text-[10px]">
              {areaInfo.label}
            </Tag>
          )}
        </div>
        <span className="text-[11px] text-slate-500 font-mono">
          Mã vị trí: {locCode}
          {locLabel ? ` • Node: ${locLabel}` : ''}
        </span>
      </div>
    );
  };

  const columns = [
    {
      title: 'Mã Lệnh & Loại yêu cầu',
      key: 'request_code',
      width: 220,
      render: (_: unknown, record: TransportRequestManagementItem) => {
        const typeInfo = REQUEST_TYPE_LABELS[record.request_type] || {
          label: record.request_type,
          color: 'default',
        };
        return (
          <div className="flex flex-col gap-1">
            <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded border border-slate-300 w-fit">
              {record.request_code}
            </span>
            <Tag color={typeInfo.color} className="w-fit m-0 text-[11px]">
              {typeInfo.label}
            </Tag>
          </div>
        );
      },
    },
    {
      title: 'Trạm / Máy CNC & Vị trí (Nguồn ➔ Đích)',
      key: 'stations',
      width: 340,
      render: (_: unknown, record: TransportRequestManagementItem) => (
        <div className="flex flex-col gap-1.5 py-0.5">
          <div className="flex items-start gap-1.5">
            <span className="text-[11px] font-semibold text-slate-400 w-10 shrink-0">
              Từ:
            </span>
            {renderStationBlock(
              record.source_location_name,
              record.source_location_code,
              record.source_location_label,
              record.source_location_type,
              record.source_machine_code,
              'Đang chờ tìm xe phù hợp',
            )}
          </div>
          <div className="flex items-start gap-1.5">
            <span className="text-[11px] font-semibold text-brand-primary w-10 shrink-0">
              Đến:
            </span>
            {renderStationBlock(
              record.destination_location_name,
              record.destination_location_code,
              record.destination_location_label,
              record.destination_location_type,
              record.destination_machine_code,
              'Đang chờ ô trống (Rửa / Bãi trống)',
            )}
          </div>
        </div>
      ),
    },
    {
      title: 'Model & Công đoạn',
      key: 'model',
      width: 210,
      render: (_: unknown, record: TransportRequestManagementItem) => (
        <div className="flex flex-col gap-1">
          {record.item_name ? (
            <>
              <span className="font-semibold text-slate-800 text-xs">
                {record.item_name}
              </span>
              <span className="text-[11px] text-slate-500 font-mono">
                SKU: {record.item_sku}
              </span>
            </>
          ) : (
            <span className="text-xs text-slate-400 italic">Xe rỗng thu hồi</span>
          )}
          <Tag color="blue" className="w-fit m-0 text-[11px]">
            {record.required_stage_level === 0
              ? 'Phôi thô (Lv 0)'
              : `Công đoạn Lv ${record.required_stage_level}`}
          </Tag>
        </div>
      ),
    },
    {
      title: 'Rack & Nhiệm vụ AMR',
      key: 'rack_mission',
      width: 190,
      render: (_: unknown, record: TransportRequestManagementItem) => (
        <div className="flex flex-col gap-1">
          {record.container_code ? (
            <span className="font-mono text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 w-fit">
              Rack: {record.container_code}
            </span>
          ) : (
            <span className="text-xs text-amber-600 italic">Chưa gán Rack</span>
          )}
          {record.mission_code && (
            <div className="text-[11px] font-mono text-slate-600">
              AMR: <strong>{record.mission_code}</strong>
              {record.robot_id ? ` (${record.robot_id})` : ''}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 200,
      render: (_: unknown, record: TransportRequestManagementItem) => {
        const meta = STATUS_META[record.status] || {
          label: record.status,
          color: 'default',
        };
        return (
          <div className="flex flex-col gap-1">
            <Tag icon={meta.icon} color={meta.color} className="w-fit m-0">
              {meta.label}
            </Tag>
            {record.fleet_task_status && (
              <span className="text-[11px] text-slate-500 font-mono">
                Fleet: {record.fleet_task_status}
              </span>
            )}
          </div>
        );
      },
    },
    {
      title: 'Người tạo & Thời gian',
      key: 'creator',
      width: 170,
      render: (_: unknown, record: TransportRequestManagementItem) => (
        <div className="flex flex-col gap-0.5 text-xs">
          <div className="font-medium text-slate-700 flex items-center gap-1">
            <UserOutlined className="text-slate-400" />
            <span>{record.created_by_username || 'Hệ thống'}</span>
          </div>
          <span className="text-[11px] text-slate-500">
            {record.created_at
              ? new Date(record.created_at).toLocaleString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  day: '2-digit',
                  month: '2-digit',
                })
              : '--'}
          </span>
        </div>
      ),
    },
    {
      title: 'Thao tác',
      key: 'actions',
      width: 140,
      fixed: 'right' as const,
      render: (_: unknown, record: TransportRequestManagementItem) => {
        const disabled = !record.can_cancel;
        return (
          <Tooltip title={record.cancel_block_reason || undefined}>
            <span>
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                disabled={disabled}
                onClick={() => {
                  setCancellingReq(record);
                  setCancelErrorMsg(null);
                }}
              >
                Hủy lệnh
              </Button>
            </span>
          </Tooltip>
        );
      },
    },
  ];

  return (
    <div className="space-y-6 p-4 md:p-6">
      <Hero
        title="Quản lý Lệnh Điều Xe & Hàng Đợi (Request)"
        subtitle="Theo dõi các yêu cầu gọi phôi / chuyển trạm của từng máy CNC, khu Rửa và hỗ trợ Admin hủy lệnh tức thì (tự động mở khóa Rack và cập nhật màn hình PDA của Operator)."
      />

      {/* Thống kê nhanh */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card className="p-3.5 border border-slate-200/80 shadow-xs">
          <div className="text-xs text-slate-500 font-medium">
            Tổng lệnh đang hoạt động
          </div>
          <div className="mt-1 text-2xl font-bold text-slate-900">
            {stats.totalActive}
          </div>
        </Card>
        <Card className="p-3.5 border border-amber-200/80 bg-amber-50/30 shadow-xs">
          <div className="text-xs text-amber-600 font-medium">
            Đang chờ xe phôi (WAITING_CART)
          </div>
          <div className="mt-1 text-2xl font-bold text-amber-700">
            {stats.waitingCart}
          </div>
        </Card>
        <Card className="p-3.5 border border-yellow-200/80 bg-yellow-50/30 shadow-xs">
          <div className="text-xs text-yellow-700 font-medium">
            Đang chờ ô trống (WAITING_SLOT)
          </div>
          <div className="mt-1 text-2xl font-bold text-yellow-800">
            {stats.waitingSlot}
          </div>
        </Card>
        <Card className="p-3.5 border border-blue-200/80 bg-blue-50/30 shadow-xs">
          <div className="text-xs text-blue-600 font-medium">
            Đang điều xe AMR (in_progress)
          </div>
          <div className="mt-1 text-2xl font-bold text-blue-700">
            {stats.inProgress}
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Tìm theo Máy CNC, vị trí, mã lệnh, mã Rack, Model, người tạo..."
              prefix={<SearchOutlined className="text-slate-400" />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              className="w-full sm:w-80"
            />
            <Select
              value={statusFilter}
              onChange={(val) => setStatusFilter(val)}
              className="w-full sm:w-56"
              options={[
                { value: 'ALL', label: 'Tất cả trạng thái' },
                {
                  value: 'queued_for_cart',
                  label: 'Đang chờ xe (WAITING_CART)',
                },
                {
                  value: 'queued_for_slot',
                  label: 'Đang chờ ô trống (WAITING_SLOT)',
                },
                { value: 'in_progress', label: 'Đang điều xe AMR' },
                { value: 'cancelled', label: 'Đã hủy' },
                { value: 'completed', label: 'Đã hoàn thành' },
                { value: 'failed', label: 'Thất bại' },
              ]}
            />
            <Select
              value={typeFilter}
              onChange={(val) => setTypeFilter(val)}
              className="w-full sm:w-52"
              options={[
                { value: 'ALL', label: 'Tất cả loại lệnh' },
                {
                  value: 'PULL_RAW_MATERIAL',
                  label: 'Gọi phôi thô vào CNC',
                },
                {
                  value: 'MOVE_BETWEEN_CNC',
                  label: 'Chuyển giữa máy CNC',
                },
                { value: 'MOVE_TO_WASH', label: 'Chuyển sang Tẩy Rửa' },
                { value: 'RETURN_EMPTY_CART', label: 'Trả xe rỗng về bãi' },
              ]}
            />
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
              <Switch
                size="small"
                checked={includeHistory}
                onChange={(checked) => setIncludeHistory(checked)}
              />
              <span>Hiển thị cả lịch sử đã xong / đã hủy</span>
            </label>
          </div>

          <Button
            icon={<ReloadOutlined spin={isFetching} />}
            onClick={() => refetch()}
          >
            Làm mới
          </Button>
        </div>

        <Table
          rowKey="id"
          loading={isLoading}
          columns={columns}
          dataSource={filteredRequests}
          scroll={{ x: 1250 }}
          pagination={{
            pageSize: 15,
            showSizeChanger: true,
            showTotal: (total) => `Tổng ${total} yêu cầu`,
          }}
          locale={{
            emptyText: (
              <div className="py-8 text-center text-slate-400">
                <InboxOutlined className="text-3xl mb-2 block mx-auto" />
                <span>
                  Hiện không có yêu cầu gọi phôi / vận chuyển nào đang chờ xử lý
                </span>
              </div>
            ),
          }}
        />
      </Card>

      {/* Modal xác nhận hủy yêu cầu */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-red-600">
            <ExclamationCircleOutlined />
            <span>
              Xác nhận hủy yêu cầu:{' '}
              <strong className="font-mono">
                {cancellingReq?.request_code}
              </strong>
            </span>
          </div>
        }
        open={Boolean(cancellingReq)}
        onCancel={() => {
          setCancellingReq(null);
          setCancelErrorMsg(null);
        }}
        onOk={() => {
          if (!cancellingReq) return;
          setCancelErrorMsg(null);
          cancelMutation.mutate(cancellingReq.id);
        }}
        confirmLoading={cancelMutation.isPending}
        okText="Xác nhận Hủy lệnh"
        okButtonProps={{ danger: true }}
        cancelText="Đóng"
        destroyOnClose
      >
        {cancellingReq && (
          <div className="space-y-4 pt-2">
            <Alert
              type="warning"
              showIcon
              message="Đồng bộ tức thì tới màn hình PDA của Operator & KUKA Fleet"
              description="Khi hủy lệnh này, hệ thống sẽ xóa yêu cầu khỏi hàng đợi tự động, mở khóa xe phôi (nếu có), gửi lệnh dừng nhiệm vụ sang KUKA Fleet (nếu AMR đang chạy) và tự động làm mới màn hình PDA của công nhân tại trạm đó ngay lập tức."
            />

            {cancelErrorMsg && (
              <Alert
                type="error"
                showIcon
                message="Không thể hủy yêu cầu"
                description={cancelErrorMsg}
              />
            )}

            <div className="rounded-lg bg-slate-50 p-3.5 text-xs space-y-2 border border-slate-200">
              <div>
                <span className="text-slate-500">Mã yêu cầu:</span>{' '}
                <strong className="font-mono text-slate-900">
                  {cancellingReq.request_code}
                </strong>
              </div>
              <div>
                <span className="text-slate-500">Trạm nguồn ➔ Trạm đích:</span>{' '}
                <strong className="text-slate-800">
                  {cancellingReq.source_machine_code
                    ? `[${cancellingReq.source_machine_code}] `
                    : ''}
                  {cancellingReq.source_location_name ||
                    cancellingReq.source_location_code ||
                    'Đang chờ tìm xe'}{' '}
                  <SwapRightOutlined className="mx-1 text-brand-primary" />{' '}
                  {cancellingReq.destination_machine_code
                    ? `[${cancellingReq.destination_machine_code}] `
                    : ''}
                  {cancellingReq.destination_location_name ||
                    cancellingReq.destination_location_code ||
                    'Đang chờ ô trống'}
                </strong>
              </div>
              {cancellingReq.item_name && (
                <div>
                  <span className="text-slate-500">Model &amp; Công đoạn:</span>{' '}
                  <strong className="text-slate-800">
                    {cancellingReq.item_name} ({cancellingReq.item_sku}) — Lv{' '}
                    {cancellingReq.required_stage_level}
                  </strong>
                </div>
              )}
              {cancellingReq.container_code && (
                <div>
                  <span className="text-slate-500">Rack đang gán:</span>{' '}
                  <strong className="font-mono text-emerald-700">
                    {cancellingReq.container_code}
                  </strong>
                </div>
              )}
              {cancellingReq.mission_code && (
                <div>
                  <span className="text-slate-500">Nhiệm vụ AMR:</span>{' '}
                  <strong className="font-mono text-blue-700">
                    {cancellingReq.mission_code} ({cancellingReq.fleet_task_status})
                  </strong>
                </div>
              )}
              <div>
                <span className="text-slate-500">Người yêu cầu:</span>{' '}
                <strong className="text-slate-800">
                  {cancellingReq.created_by_username || 'Hệ thống'}
                </strong>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
