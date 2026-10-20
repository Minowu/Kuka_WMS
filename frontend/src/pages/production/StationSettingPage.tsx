import { useState } from 'react';
import {
  Card,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Table,
} from '@/components/ui';
import { Tag, Tabs, Badge, Switch, Popconfirm, Tooltip } from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  StopOutlined,
  EnvironmentOutlined,
  InboxOutlined,
  ExperimentOutlined,
  CarOutlined,
  InfoCircleOutlined,
  ClusterOutlined,
  MinusCircleOutlined,
} from '@ant-design/icons';
import Hero from '@/components/shared/Hero';
import {
  useStationCatalog,
  useAvailableNodes,
  useCreateMachine,
  useUpdateMachine,
  useDeleteMachine,
  useCreateStationLocation,
  useUpdateStationLocation,
  useDeleteStationLocation,
} from '@/hooks/useMachines';
import type {
  StationCatalogItem,
  MachineCatalogGroup,
  AvailableMapNode,
  SlotConfigInput,
} from '@/types/machine';

interface SlotFormItem {
  position_index: number;
  location_code: string;
  node_label?: string;
  map_x?: number;
  map_y?: number;
}

export default function StationSettingPage() {
  const { data: catalog, isLoading, refetch } = useStationCatalog();
  const { data: availableNodes = [] } = useAvailableNodes();

  const createMachineMutation = useCreateMachine();
  const updateMachineMutation = useUpdateMachine();
  const deleteMachineMutation = useDeleteMachine();

  const createLocationMutation = useCreateStationLocation();
  const updateLocationMutation = useUpdateStationLocation();
  const deleteLocationMutation = useDeleteStationLocation();

  // Active Tab: 'raw_material' | 'cnc' | 'washing_buffer'
  const [activeTab, setActiveTab] = useState<string>('raw_material');

  // Modal States
  // 1. Raw Material
  const [isRawModalOpen, setIsRawModalOpen] = useState(false);
  const [editingRaw, setEditingRaw] = useState<StationCatalogItem | null>(null);
  const [rawForm] = Form.useForm();

  // 2. CNC Machine
  const [isCncCreateOpen, setIsCncCreateOpen] = useState(false);
  const [editingCnc, setEditingCnc] = useState<MachineCatalogGroup | null>(null);
  const [cncForm] = Form.useForm();
  const [cncEditForm] = Form.useForm();
  const [createSlots, setCreateSlots] = useState<SlotFormItem[]>([
    { position_index: 1, location_code: '' },
    { position_index: 2, location_code: '' },
  ]);
  const [editSlots, setEditSlots] = useState<SlotFormItem[]>([]);

  // 3. Washing & Buffer
  const [isWashModalOpen, setIsWashModalOpen] = useState(false);
  const [editingWash, setEditingWash] = useState<StationCatalogItem | null>(null);
  const [washForm] = Form.useForm();

  const [isBufferModalOpen, setIsBufferModalOpen] = useState(false);
  const [editingBuffer, setEditingBuffer] = useState<StationCatalogItem | null>(null);
  const [bufferForm] = Form.useForm();

  // Helper options for map node select
  const nodeOptions = availableNodes.map((n) => ({
    value: n.node_label,
    label: `Node ${n.node_label} (${(n.map_x / 1000).toFixed(1)}m, ${(n.map_y / 1000).toFixed(1)}m)${
      n.is_assigned ? ' [Đang dùng]' : ''
    }`,
    node: n,
  }));

  // =========================================================================
  // HANDLERS: TAB 1 - KHU CẤP PHÔI
  // =========================================================================
  const handleOpenCreateRaw = () => {
    setEditingRaw(null);
    rawForm.resetFields();
    rawForm.setFieldsValue({
      location_code: `VT-0${(catalog?.raw_materials?.length || 0) + 1}`,
      location_name: `Ô Cấp Phôi ${(catalog?.raw_materials?.length || 0) + 1}`,
    });
    setIsRawModalOpen(true);
  };

  const handleOpenEditRaw = (item: StationCatalogItem) => {
    setEditingRaw(item);
    rawForm.resetFields();
    rawForm.setFieldsValue({
      location_code: item.location_code,
      location_name: item.location_name || '',
      node_label: item.node_label || undefined,
      is_active: item.is_active,
    });
    setIsRawModalOpen(true);
  };

  const handleSubmitRaw = async () => {
    try {
      const values = await rawForm.validateFields();
      const selectedNode = availableNodes.find((n) => n.node_label === values.node_label);

      if (editingRaw) {
        await updateLocationMutation.mutateAsync({
          id: editingRaw.id,
          data: {
            location_name: values.location_name,
            node_label: values.node_label,
            map_x: selectedNode ? selectedNode.map_x : editingRaw.map_x ?? undefined,
            map_y: selectedNode ? selectedNode.map_y : editingRaw.map_y ?? undefined,
            is_active: values.is_active,
          },
        });
        message.success(`Cập nhật ô cấp phôi '${editingRaw.location_code}' thành công!`);
      } else {
        await createLocationMutation.mutateAsync({
          location_code: values.location_code.trim(),
          location_name: values.location_name.trim(),
          location_type: 'RAW_MATERIAL',
          node_label: values.node_label,
          map_x: selectedNode ? selectedNode.map_x : undefined,
          map_y: selectedNode ? selectedNode.map_y : undefined,
          position_index: (catalog?.raw_materials?.length || 0) + 1,
        });
        message.success(`Thêm ô cấp phôi '${values.location_code}' thành công!`);
      }
      setIsRawModalOpen(false);
      refetch();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (!err?.errorFields) {
        message.error('Không thể lưu cấu hình ô cấp phôi');
      }
    }
  };

  const handleDeleteRaw = async (id: number, code: string) => {
    try {
      await deleteLocationMutation.mutateAsync(id);
      message.success(`Đã xóa ô cấp phôi '${code}'`);
      refetch();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Không thể xóa ô cấp phôi');
    }
  };

  // =========================================================================
  // HANDLERS: TAB 2 - KHU MÁY CNC (Hỗ trợ linh hoạt 1..3 Slots)
  // =========================================================================
  const handleOpenCreateCnc = () => {
    cncForm.resetFields();
    const nextNum = (catalog?.machines?.length || 0) + 1;
    const defaultCode = `CNC-0${nextNum}`;
    cncForm.setFieldsValue({
      machine_code: defaultCode,
      machine_name: `Máy Phay CNC 0${nextNum}`,
    });
    setCreateSlots([
      { position_index: 1, location_code: `${defaultCode}-POS1` },
      { position_index: 2, location_code: `${defaultCode}-POS2` },
    ]);
    setIsCncCreateOpen(true);
  };

  const handleCncCodeChange = (codeVal: string) => {
    const upper = (codeVal || '').toUpperCase().trim();
    setCreateSlots((prev) =>
      prev.map((slot) => ({
        ...slot,
        location_code: `${upper}-POS${slot.position_index}`,
      }))
    );
  };

  const handleAddCreateSlot = () => {
    if (createSlots.length >= 3) {
      message.warning('Mỗi máy CNC hỗ trợ tối đa 3 vị trí đỗ vật lý (POS1, POS2, POS3)!');
      return;
    }
    const nextIdx = createSlots.length + 1;
    const code = cncForm.getFieldValue('machine_code') || 'CNC-XX';
    setCreateSlots((prev) => [
      ...prev,
      {
        position_index: nextIdx,
        location_code: `${code.toUpperCase().trim()}-POS${nextIdx}`,
      },
    ]);
  };

  const handleRemoveCreateSlot = (indexToRemove: number) => {
    if (createSlots.length <= 1) {
      message.warning('Máy CNC cần có ít nhất 1 vị trí đỗ!');
      return;
    }
    const filtered = createSlots.filter((_, idx) => idx !== indexToRemove);
    const reindexed = filtered.map((s, idx) => ({
      ...s,
      position_index: idx + 1,
      location_code: `${(cncForm.getFieldValue('machine_code') || 'CNC-XX').toUpperCase().trim()}-POS${
        idx + 1
      }`,
    }));
    setCreateSlots(reindexed);
  };

  const handleCreateSlotNodeChange = (slotIndex: number, nodeLabel: string) => {
    const selectedNode = availableNodes.find((n) => n.node_label === nodeLabel);
    setCreateSlots((prev) =>
      prev.map((s, idx) =>
        idx === slotIndex
          ? {
              ...s,
              node_label: nodeLabel,
              map_x: selectedNode?.map_x,
              map_y: selectedNode?.map_y,
            }
          : s
      )
    );
  };

  const handleSubmitCreateCnc = async () => {
    try {
      const values = await cncForm.validateFields();
      const code = values.machine_code.toUpperCase().trim();

      const slotsPayload: SlotConfigInput[] = createSlots.map((s) => ({
        position_index: s.position_index,
        location_code: s.location_code || `${code}-POS${s.position_index}`,
        node_label: s.node_label,
        map_x: s.map_x,
        map_y: s.map_y,
      }));

      await createMachineMutation.mutateAsync({
        machine_code: code,
        machine_name: values.machine_name.trim(),
        slots: slotsPayload,
      });

      message.success(`Thêm máy '${code}' cùng ${createSlots.length} vị trí đỗ thành công!`);
      setIsCncCreateOpen(false);
      refetch();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (!err?.errorFields) {
        message.error('Không thể tạo máy CNC mới');
      }
    }
  };

  const handleOpenEditCnc = (m: MachineCatalogGroup) => {
    setEditingCnc(m);
    cncEditForm.resetFields();
    cncEditForm.setFieldsValue({
      machine_name: m.machine_name || `Máy ${m.machine_code}`,
      is_active: m.is_active,
    });

    const currentSlots: SlotFormItem[] = (m.slots || []).map((s, idx) => ({
      position_index: s.position_index || idx + 1,
      location_code: s.location_code,
      node_label: s.node_label || undefined,
      map_x: s.map_x || undefined,
      map_y: s.map_y || undefined,
    }));

    if (currentSlots.length === 0) {
      currentSlots.push(
        { position_index: 1, location_code: `${m.machine_code}-POS1` },
        { position_index: 2, location_code: `${m.machine_code}-POS2` }
      );
    }
    setEditSlots(currentSlots);
  };

  const handleAddEditSlot = () => {
    if (editSlots.length >= 3) {
      message.warning('Mỗi máy CNC hỗ trợ tối đa 3 vị trí đỗ (POS1, POS2, POS3)!');
      return;
    }
    if (!editingCnc) return;
    const nextIdx = editSlots.length + 1;
    setEditSlots((prev) => [
      ...prev,
      {
        position_index: nextIdx,
        location_code: `${editingCnc.machine_code}-POS${nextIdx}`,
      },
    ]);
  };

  const handleRemoveEditSlot = (indexToRemove: number) => {
    if (editSlots.length <= 1) {
      message.warning('Máy CNC cần ít nhất 1 vị trí đỗ!');
      return;
    }
    if (!editingCnc) return;
    const filtered = editSlots.filter((_, idx) => idx !== indexToRemove);
    const reindexed = filtered.map((s, idx) => ({
      ...s,
      position_index: idx + 1,
      location_code: `${editingCnc.machine_code}-POS${idx + 1}`,
    }));
    setEditSlots(reindexed);
  };

  const handleEditSlotNodeChange = (slotIndex: number, nodeLabel: string) => {
    const selectedNode = availableNodes.find((n) => n.node_label === nodeLabel);
    setEditSlots((prev) =>
      prev.map((s, idx) =>
        idx === slotIndex
          ? {
              ...s,
              node_label: nodeLabel,
              map_x: selectedNode?.map_x,
              map_y: selectedNode?.map_y,
            }
          : s
      )
    );
  };

  const handleSubmitEditCnc = async () => {
    if (!editingCnc) return;
    try {
      const values = await cncEditForm.validateFields();
      const slotsPayload: SlotConfigInput[] = editSlots.map((s) => ({
        position_index: s.position_index,
        location_code: s.location_code,
        node_label: s.node_label,
        map_x: s.map_x,
        map_y: s.map_y,
      }));

      await updateMachineMutation.mutateAsync({
        id: editingCnc.id,
        data: {
          machine_name: values.machine_name.trim(),
          is_active: values.is_active,
          slots: slotsPayload,
        },
      });

      message.success(`Cập nhật cấu hình máy '${editingCnc.machine_code}' thành công!`);
      setEditingCnc(null);
      refetch();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (!err?.errorFields) {
        message.error('Không thể cập nhật máy CNC');
      }
    }
  };

  const handleDeleteCnc = async (id: number, code: string) => {
    try {
      await deleteMachineMutation.mutateAsync(id);
      message.success(`Đã xóa máy CNC '${code}'`);
      refetch();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Không thể xóa máy CNC');
    }
  };

  // =========================================================================
  // HANDLERS: TAB 3 - KHU TẨY RỬA & BÃI ĐỆM XE RỖNG
  // =========================================================================
  const handleOpenCreateWash = () => {
    setEditingWash(null);
    washForm.resetFields();
    const count = (catalog?.washing_slots?.length || 0) + 1;
    washForm.setFieldsValue({
      location_code: `WASH-0${count}`,
      location_name: `Trạm Tẩy Rửa 0${count}`,
    });
    setIsWashModalOpen(true);
  };

  const handleOpenEditWash = (item: StationCatalogItem) => {
    setEditingWash(item);
    washForm.resetFields();
    washForm.setFieldsValue({
      location_code: item.location_code,
      location_name: item.location_name || '',
      node_label: item.node_label || undefined,
      is_active: item.is_active,
    });
    setIsWashModalOpen(true);
  };

  const handleSubmitWash = async () => {
    try {
      const values = await washForm.validateFields();
      const selectedNode = availableNodes.find((n) => n.node_label === values.node_label);

      if (editingWash) {
        await updateLocationMutation.mutateAsync({
          id: editingWash.id,
          data: {
            location_name: values.location_name,
            node_label: values.node_label,
            map_x: selectedNode ? selectedNode.map_x : editingWash.map_x ?? undefined,
            map_y: selectedNode ? selectedNode.map_y : editingWash.map_y ?? undefined,
            is_active: values.is_active,
          },
        });
        message.success(`Cập nhật slot tẩy rửa '${editingWash.location_code}' thành công!`);
      } else {
        await createLocationMutation.mutateAsync({
          location_code: values.location_code.trim(),
          location_name: values.location_name.trim(),
          location_type: 'WASHING_SLOT',
          node_label: values.node_label,
          map_x: selectedNode ? selectedNode.map_x : undefined,
          map_y: selectedNode ? selectedNode.map_y : undefined,
          position_index: (catalog?.washing_slots?.length || 0) + 1,
        });
        message.success(`Thêm slot tẩy rửa '${values.location_code}' thành công!`);
      }
      setIsWashModalOpen(false);
      refetch();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (!err?.errorFields) {
        message.error('Không thể lưu slot tẩy rửa');
      }
    }
  };

  const handleDeleteWash = async (id: number, code: string) => {
    try {
      await deleteLocationMutation.mutateAsync(id);
      message.success(`Đã xóa slot tẩy rửa '${code}'`);
      refetch();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Không thể xóa slot tẩy rửa');
    }
  };

  // Buffer Handlers
  const bufferList = catalog?.empty_buffers || catalog?.buffer_slots || [];

  const handleOpenCreateBuffer = () => {
    setEditingBuffer(null);
    bufferForm.resetFields();
    const count = bufferList.length + 1;
    bufferForm.setFieldsValue({
      location_code: `EMPTY-0${count}`,
      location_name: `Bãi Đệm Xe Rỗng 0${count}`,
    });
    setIsBufferModalOpen(true);
  };

  const handleOpenEditBuffer = (item: StationCatalogItem) => {
    setEditingBuffer(item);
    bufferForm.resetFields();
    bufferForm.setFieldsValue({
      location_code: item.location_code,
      location_name: item.location_name || '',
      node_label: item.node_label || undefined,
      is_active: item.is_active,
    });
    setIsBufferModalOpen(true);
  };

  const handleSubmitBuffer = async () => {
    try {
      const values = await bufferForm.validateFields();
      const selectedNode = availableNodes.find((n) => n.node_label === values.node_label);

      if (editingBuffer) {
        await updateLocationMutation.mutateAsync({
          id: editingBuffer.id,
          data: {
            location_name: values.location_name,
            node_label: values.node_label,
            map_x: selectedNode ? selectedNode.map_x : editingBuffer.map_x ?? undefined,
            map_y: selectedNode ? selectedNode.map_y : editingBuffer.map_y ?? undefined,
            is_active: values.is_active,
          },
        });
        message.success(`Cập nhật bãi đệm '${editingBuffer.location_code}' thành công!`);
      } else {
        await createLocationMutation.mutateAsync({
          location_code: values.location_code.trim(),
          location_name: values.location_name.trim(),
          location_type: 'EMPTY_CART_BUFFER',
          node_label: values.node_label,
          map_x: selectedNode ? selectedNode.map_x : undefined,
          map_y: selectedNode ? selectedNode.map_y : undefined,
          position_index: bufferList.length + 1,
        });
        message.success(`Thêm bãi đệm '${values.location_code}' thành công!`);
      }
      setIsBufferModalOpen(false);
      refetch();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (!err?.errorFields) {
        message.error('Không thể lưu bãi đệm xe rỗng');
      }
    }
  };

  const handleDeleteBuffer = async (id: number, code: string) => {
    try {
      await deleteLocationMutation.mutateAsync(id);
      message.success(`Đã xóa bãi đệm '${code}'`);
      refetch();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Không thể xóa bãi đệm');
    }
  };

  // Helper badge for positions P1, P2, P3
  const renderPosBadge = (posIndex: number | null) => {
    if (posIndex === 1) {
      return (
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-700 border border-blue-200">
          P1
        </span>
      );
    }
    if (posIndex === 2) {
      return (
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-700 border border-purple-200">
          P2
        </span>
      );
    }
    if (posIndex === 3) {
      return (
        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-700 border border-amber-200">
          P3
        </span>
      );
    }
    return (
      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
        P{posIndex || '?'}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <Hero
        title="Cấu Hình Trạm & Phân Khu Xưởng"
        subtitle="Quản lý các điểm đỗ vật lý gắn với Node Map KUKA: Khu Cấp Phôi, Khu Máy CNC (hỗ trợ 1..3 slots) và Khu Tẩy Rửa / Bãi Đệm"
      />

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        className="[&_.ant-tabs-nav]:!mb-4 [&_.ant-tabs-tab]:!font-semibold [&_.ant-tabs-tab-active]:!text-brand-primary"
        items={[
          {
            key: 'raw_material',
            label: (
              <span className="flex items-center gap-2">
                <InboxOutlined className="text-amber-600 text-base" />
                <span>Khu Cấp Phôi ({catalog?.raw_materials?.length || 0})</span>
              </span>
            ),
            children: (
              <div className="space-y-4">
                <div className="flex items-center justify-between bg-amber-50/60 border border-amber-200/80 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <InfoCircleOutlined className="text-amber-600 text-xl shrink-0" />
                    <div className="text-xs text-amber-900 leading-relaxed">
                      <span className="font-bold">Khu Cấp Phôi (Nguyên Liệu):</span> Các ô tiếp nhận xe Rack gá phôi thô từ kho. AMR sẽ tự động di chuyển đến các vị trí này để nhận phôi khi máy CNC kích hoạt lệnh gọi.
                    </div>
                  </div>
                  <Button
                    onClick={handleOpenCreateRaw}
                    icon={<PlusOutlined />}
                    className="!bg-amber-600 hover:!bg-amber-700 !border-none !text-white !h-9 !px-4 !rounded-lg font-semibold shrink-0"
                  >
                    Thêm Ô Cấp Phôi
                  </Button>
                </div>

                <Card className="rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                  <Table
                    loading={isLoading}
                    dataSource={catalog?.raw_materials || []}
                    rowKey="id"
                    pagination={false}
                    className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold"
                    columns={[
                      {
                        title: 'Mã Ô',
                        dataIndex: 'location_code',
                        key: 'location_code',
                        width: 140,
                        render: (text: string) => (
                          <span className="font-mono font-bold text-amber-900 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200">
                            {text}
                          </span>
                        ),
                      },
                      {
                        title: 'Tên Vị Trí',
                        dataIndex: 'location_name',
                        key: 'location_name',
                        render: (text: string) => (
                          <span className="font-medium text-slate-800">{text || '—'}</span>
                        ),
                      },
                      {
                        title: 'Node Map Liên Kết',
                        key: 'node_label',
                        width: 180,
                        render: (_: any, record: StationCatalogItem) => (
                          <div className="flex items-center gap-1.5 font-mono text-xs">
                            <Tag color="cyan" className="!font-bold !m-0">
                              Node {record.node_label || '--'}
                            </Tag>
                          </div>
                        ),
                      },
                      {
                        title: 'Tọa Độ Thực Tế (Map X, Y)',
                        key: 'coords',
                        width: 220,
                        render: (_: any, record: StationCatalogItem) => (
                          <div className="text-xs font-mono text-slate-600 flex items-center gap-1">
                            <EnvironmentOutlined className="text-slate-400" />
                            <span>
                              {record.map_x != null && record.map_y != null
                                ? `(${record.map_x}, ${record.map_y}) mm`
                                : 'Chưa gắn tọa độ'}
                            </span>
                          </div>
                        ),
                      },
                      {
                        title: 'Trạng Thái',
                        dataIndex: 'is_active',
                        key: 'is_active',
                        width: 130,
                        render: (active: boolean) =>
                          active ? (
                            <Tag color="success" icon={<CheckCircleOutlined />}>
                              Hoạt động
                            </Tag>
                          ) : (
                            <Tag color="default" icon={<StopOutlined />}>
                              Tạm dừng
                            </Tag>
                          ),
                      },
                      {
                        title: 'Thao Tác',
                        key: 'actions',
                        width: 140,
                        align: 'center',
                        render: (_: any, record: StationCatalogItem) => (
                          <Space size="small">
                            <Button
                              variant="outline"
                              size="sm"
                              icon={<EditOutlined />}
                              onClick={() => handleOpenEditRaw(record)}
                              className="!h-8 !px-2 text-slate-600 hover:text-brand-primary"
                              title="Sửa ô"
                            />
                            <Popconfirm
                              title="Xóa ô cấp phôi này?"
                              description="Bạn có chắc chắn muốn xóa vị trí này không?"
                              okText="Xóa"
                              cancelText="Hủy"
                              okButtonProps={{ danger: true }}
                              onConfirm={() => handleDeleteRaw(record.id, record.location_code)}
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                icon={<DeleteOutlined className="text-red-500" />}
                                className="!h-8 !px-2 hover:border-red-400"
                                title="Xóa ô"
                              />
                            </Popconfirm>
                          </Space>
                        ),
                      },
                    ]}
                  />
                </Card>
              </div>
            ),
          },
          {
            key: 'cnc',
            label: (
              <span className="flex items-center gap-2">
                <ToolOutlined className="text-brand-primary text-base" />
                <span>Khu Máy CNC ({catalog?.machines?.length || 0})</span>
              </span>
            ),
            children: (
              <div className="space-y-4">
                <div className="flex items-center justify-between bg-blue-50/70 border border-blue-200 rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <InfoCircleOutlined className="text-blue-600 text-xl shrink-0" />
                    <div className="text-xs text-blue-900 leading-relaxed">
                      <span className="font-bold">Mô hình CNC linh hoạt 1..3 Slots:</span> Mỗi máy CNC có thể cấu hình linh hoạt từ 1 đến 3 vị trí đỗ vật lý (<span className="font-semibold text-blue-700">POS1, POS2, POS3</span>), gắn tương ứng với Node Map KUKA. Công đoạn gia công không gắn cứng vào máy mà được quản lý linh hoạt trong trang <span className="font-semibold underline">Quy trình (Route)</span>.
                    </div>
                  </div>
                  <Button
                    onClick={handleOpenCreateCnc}
                    icon={<PlusOutlined />}
                    className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none !text-white !h-9 !px-4 !rounded-lg font-semibold shrink-0"
                  >
                    Thêm Máy CNC
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-5">
                  {(catalog?.machines || []).map((machine) => {
                    const slots = machine.slots || [];
                    return (
                      <Card
                        key={machine.id}
                        className="shadow-sm border-slate-200/80 rounded-xl hover:shadow-md transition-shadow overflow-hidden bg-white"
                      >
                        {/* Machine Header */}
                        <div className="flex items-start justify-between border-b border-slate-100 pb-3 mb-3">
                          <div className="flex items-center gap-3">
                            <div className="w-11 h-11 rounded-xl bg-orange-50 border border-orange-200 flex items-center justify-center text-brand-primary text-xl font-bold">
                              <ToolOutlined />
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-lg font-bold text-slate-800">{machine.machine_code}</span>
                                {machine.is_active ? (
                                  <Tag color="success" icon={<CheckCircleOutlined />}>
                                    Hoạt động
                                  </Tag>
                                ) : (
                                  <Tag color="default" icon={<StopOutlined />}>
                                    Tạm dừng
                                  </Tag>
                                )}
                              </div>
                              <div className="text-xs text-slate-500 font-medium mt-0.5">
                                {machine.machine_name || `Máy ${machine.machine_code}`}
                              </div>
                            </div>
                          </div>

                          <Space size="small">
                            <Button
                              variant="outline"
                              size="sm"
                              icon={<EditOutlined />}
                              onClick={() => handleOpenEditCnc(machine)}
                              className="!h-8 !px-2.5 !rounded-lg text-slate-600 hover:text-brand-primary"
                            >
                              Sửa
                            </Button>
                            <Popconfirm
                              title={`Xóa máy CNC ${machine.machine_code}?`}
                              description="Xóa máy sẽ đồng thời xóa các vị trí đỗ liên kết."
                              okText="Xóa"
                              cancelText="Hủy"
                              okButtonProps={{ danger: true }}
                              onConfirm={() => handleDeleteCnc(machine.id, machine.machine_code)}
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                icon={<DeleteOutlined className="text-red-500" />}
                                className="!h-8 !px-2 hover:border-red-400"
                              />
                            </Popconfirm>
                          </Space>
                        </div>

                        {/* Physical Slots (1..3 Slots) */}
                        <div>
                          <div className="flex items-center justify-between text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                            <span>Vị trí đỗ vật lý ({slots.length} Slots)</span>
                            <span className="text-slate-400 font-normal">Gắn Node Map KUKA</span>
                          </div>

                          <div className={`grid gap-2.5 ${slots.length === 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
                            {slots.map((slot, sIdx) => {
                              const pos = slot.position_index || sIdx + 1;
                              const bgClass =
                                pos === 1
                                  ? 'border-blue-200 bg-blue-50/30'
                                  : pos === 2
                                  ? 'border-purple-200 bg-purple-50/30'
                                  : 'border-amber-200 bg-amber-50/30';

                              return (
                                <div key={slot.id || sIdx} className={`border rounded-lg p-2.5 ${bgClass}`}>
                                  <div className="flex items-center justify-between mb-1">
                                    <div className="flex items-center gap-1.5">
                                      {renderPosBadge(pos)}
                                      <span className="font-mono text-xs font-bold text-slate-800 truncate">
                                        {slot.location_code}
                                      </span>
                                    </div>
                                    <Badge status="processing" color={pos === 1 ? '#3B82F6' : pos === 2 ? '#8B5CF6' : '#F59E0B'} />
                                  </div>

                                  <div className="text-[11px] text-slate-600 mt-1.5 space-y-0.5">
                                    <div className="flex items-center justify-between">
                                      <span className="text-slate-400">Node:</span>
                                      <span className="font-mono font-semibold text-slate-700">
                                        {slot.node_label ? `Node ${slot.node_label}` : 'Chưa gán'}
                                      </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                      <span className="text-slate-400">Tọa độ:</span>
                                      <span className="font-mono text-[10px] text-slate-500">
                                        {slot.map_x != null ? `${slot.map_x}, ${slot.map_y}` : '--'}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            ),
          },
          {
            key: 'washing_buffer',
            label: (
              <span className="flex items-center gap-2">
                <ExperimentOutlined className="text-emerald-600 text-base" />
                <span>Khu Tẩy Rửa & Bãi Đệm ({catalog?.washing_slots?.length || 0} / {bufferList.length})</span>
              </span>
            ),
            children: (
              <div className="space-y-6">
                <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <InfoCircleOutlined className="text-emerald-600 text-xl shrink-0" />
                    <div className="text-xs text-emerald-900 leading-relaxed">
                      <span className="font-bold">Khu Tẩy Rửa & Bãi Đệm Xe Rỗng:</span> Trạm tẩy rửa tiếp nhận xe phôi sau khi hoàn thành công đoạn CNC cuối cùng. Bãi đệm xe rỗng dùng để lưu trữ các rack rỗng sau khi dỡ phôi, sẵn sàng đưa về khu cấp phôi tiếp theo.
                    </div>
                  </div>
                </div>

                {/* Section A: Khu Tẩy Rửa */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ExperimentOutlined className="text-emerald-600 text-lg" />
                      <span className="font-bold text-slate-800 text-base">
                        1. Trạm Tẩy Rửa (Washing Slots — {catalog?.washing_slots?.length || 0} Slots)
                      </span>
                    </div>
                    <Button
                      onClick={handleOpenCreateWash}
                      icon={<PlusOutlined />}
                      className="!bg-emerald-600 hover:!bg-emerald-700 !border-none !text-white !h-8 !px-3 !rounded-lg !text-xs font-semibold"
                    >
                      Thêm Slot Tẩy Rửa
                    </Button>
                  </div>

                  <Card className="rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                    <Table
                      dataSource={catalog?.washing_slots || []}
                      rowKey="id"
                      pagination={false}
                      className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold"
                      columns={[
                        {
                          title: 'Mã Slot',
                          dataIndex: 'location_code',
                          key: 'location_code',
                          width: 140,
                          render: (text: string) => (
                            <span className="font-mono font-bold text-emerald-900 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200">
                              {text}
                            </span>
                          ),
                        },
                        {
                          title: 'Tên Slot',
                          dataIndex: 'location_name',
                          key: 'location_name',
                          render: (text: string) => <span className="font-medium text-slate-800">{text || '—'}</span>,
                        },
                        {
                          title: 'Node Map Liên Kết',
                          key: 'node_label',
                          width: 180,
                          render: (_: any, record: StationCatalogItem) => (
                            <Tag color="cyan" className="font-mono !font-bold">
                              Node {record.node_label || '--'}
                            </Tag>
                          ),
                        },
                        {
                          title: 'Tọa Độ Thực Tế (Map X, Y)',
                          key: 'coords',
                          width: 220,
                          render: (_: any, record: StationCatalogItem) => (
                            <div className="text-xs font-mono text-slate-600 flex items-center gap-1">
                              <EnvironmentOutlined className="text-slate-400" />
                              <span>
                                {record.map_x != null && record.map_y != null
                                  ? `(${record.map_x}, ${record.map_y}) mm`
                                  : 'Chưa gắn tọa độ'}
                              </span>
                            </div>
                          ),
                        },
                        {
                          title: 'Trạng Thái',
                          dataIndex: 'is_active',
                          key: 'is_active',
                          width: 130,
                          render: (active: boolean) =>
                            active ? (
                              <Tag color="success" icon={<CheckCircleOutlined />}>
                                Hoạt động
                              </Tag>
                            ) : (
                              <Tag color="default" icon={<StopOutlined />}>
                                Tạm dừng
                              </Tag>
                            ),
                        },
                        {
                          title: 'Thao Tác',
                          key: 'actions',
                          width: 130,
                          align: 'center',
                          render: (_: any, record: StationCatalogItem) => (
                            <Space size="small">
                              <Button
                                variant="outline"
                                size="sm"
                                icon={<EditOutlined />}
                                onClick={() => handleOpenEditWash(record)}
                                className="!h-8 !px-2 text-slate-600 hover:text-emerald-600"
                              />
                              <Popconfirm
                                title="Xóa slot tẩy rửa này?"
                                okText="Xóa"
                                cancelText="Hủy"
                                okButtonProps={{ danger: true }}
                                onConfirm={() => handleDeleteWash(record.id, record.location_code)}
                              >
                                <Button
                                  variant="outline"
                                  size="sm"
                                  icon={<DeleteOutlined className="text-red-500" />}
                                  className="!h-8 !px-2 hover:border-red-400"
                                />
                              </Popconfirm>
                            </Space>
                          ),
                        },
                      ]}
                    />
                  </Card>
                </div>

                {/* Section B: Bãi Đệm Xe Rỗng */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <CarOutlined className="text-blue-600 text-lg" />
                      <span className="font-bold text-slate-800 text-base">
                        2. Bãi Đệm Xe Rỗng (Empty Cart Buffers — {bufferList.length} Slots)
                      </span>
                    </div>
                    <Button
                      onClick={handleOpenCreateBuffer}
                      icon={<PlusOutlined />}
                      className="!bg-blue-600 hover:!bg-blue-700 !border-none !text-white !h-8 !px-3 !rounded-lg !text-xs font-semibold"
                    >
                      Thêm Bãi Đệm
                    </Button>
                  </div>

                  <Card className="rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                    <Table
                      dataSource={bufferList}
                      rowKey="id"
                      pagination={false}
                      className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold"
                      columns={[
                        {
                          title: 'Mã Bãi Đệm',
                          dataIndex: 'location_code',
                          key: 'location_code',
                          width: 140,
                          render: (text: string) => (
                            <span className="font-mono font-bold text-blue-900 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-200">
                              {text}
                            </span>
                          ),
                        },
                        {
                          title: 'Tên Bãi Đệm',
                          dataIndex: 'location_name',
                          key: 'location_name',
                          render: (text: string) => <span className="font-medium text-slate-800">{text || '—'}</span>,
                        },
                        {
                          title: 'Node Map Liên Kết',
                          key: 'node_label',
                          width: 180,
                          render: (_: any, record: StationCatalogItem) => (
                            <Tag color="cyan" className="font-mono !font-bold">
                              Node {record.node_label || '--'}
                            </Tag>
                          ),
                        },
                        {
                          title: 'Tọa Độ Thực Tế (Map X, Y)',
                          key: 'coords',
                          width: 220,
                          render: (_: any, record: StationCatalogItem) => (
                            <div className="text-xs font-mono text-slate-600 flex items-center gap-1">
                              <EnvironmentOutlined className="text-slate-400" />
                              <span>
                                {record.map_x != null && record.map_y != null
                                  ? `(${record.map_x}, ${record.map_y}) mm`
                                  : 'Chưa gắn tọa độ'}
                              </span>
                            </div>
                          ),
                        },
                        {
                          title: 'Trạng Thái',
                          dataIndex: 'is_active',
                          key: 'is_active',
                          width: 130,
                          render: (active: boolean) =>
                            active ? (
                              <Tag color="success" icon={<CheckCircleOutlined />}>
                                Hoạt động
                              </Tag>
                            ) : (
                              <Tag color="default" icon={<StopOutlined />}>
                                Tạm dừng
                              </Tag>
                            ),
                        },
                        {
                          title: 'Thao Tác',
                          key: 'actions',
                          width: 130,
                          align: 'center',
                          render: (_: any, record: StationCatalogItem) => (
                            <Space size="small">
                              <Button
                                variant="outline"
                                size="sm"
                                icon={<EditOutlined />}
                                onClick={() => handleOpenEditBuffer(record)}
                                className="!h-8 !px-2 text-slate-600 hover:text-blue-600"
                              />
                              <Popconfirm
                                title="Xóa bãi đệm xe rỗng này?"
                                okText="Xóa"
                                cancelText="Hủy"
                                okButtonProps={{ danger: true }}
                                onConfirm={() => handleDeleteBuffer(record.id, record.location_code)}
                              >
                                <Button
                                  variant="outline"
                                  size="sm"
                                  icon={<DeleteOutlined className="text-red-500" />}
                                  className="!h-8 !px-2 hover:border-red-400"
                                />
                              </Popconfirm>
                            </Space>
                          ),
                        },
                      ]}
                    />
                  </Card>
                </div>
              </div>
            ),
          },
        ]}
      />

      {/* ========================================================================= */}
      {/* MODAL 1: THÊM / SỬA Ô CẤP PHÔI */}
      {/* ========================================================================= */}
      <Modal
        title={editingRaw ? `Chỉnh sửa ô '${editingRaw.location_code}'` : 'Thêm Ô Cấp Phôi (Nguyên Liệu)'}
        open={isRawModalOpen}
        onCancel={() => setIsRawModalOpen(false)}
        onOk={handleSubmitRaw}
        confirmLoading={createLocationMutation.isPending || updateLocationMutation.isPending}
        okText={editingRaw ? 'Lưu thay đổi' : 'Thêm ô'}
        cancelText="Hủy"
        centered
        width={480}
      >
        <Form form={rawForm} layout="vertical" className="mt-4">
          <Form.Item
            name="location_code"
            label="Mã ô cấp phôi"
            rules={[
              { required: true, message: 'Vui lòng nhập mã ô!' },
              { pattern: /^[A-Z0-9_-]+$/, message: 'Mã chỉ gồm chữ hoa, số và dấu gạch nối (VD: VT-01)' },
            ]}
          >
            <Input placeholder="Ví dụ: VT-01" className="uppercase" disabled={!!editingRaw} />
          </Form.Item>

          <Form.Item
            name="location_name"
            label="Tên hiển thị ô"
            rules={[{ required: true, message: 'Vui lòng nhập tên ô!' }]}
          >
            <Input placeholder="Ví dụ: Ô Cấp Phôi VT-01" />
          </Form.Item>

          <Form.Item
            name="node_label"
            label="Chọn Node Map KUKA liên kết"
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <Select
              showSearch
              placeholder="Chọn điểm đỗ Node trên Map"
              options={nodeOptions}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          {editingRaw && (
            <Form.Item name="is_active" label="Trạng thái hoạt động" valuePropName="checked">
              <Switch checkedChildren="Hoạt động" unCheckedChildren="Tạm dừng" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL 2: THÊM MÁY CNC (Hỗ trợ cấu hình 1..3 Slots) */}
      {/* ========================================================================= */}
      <Modal
        title="Thêm Máy CNC Mới & Cấu hình Vị trí Đỗ"
        open={isCncCreateOpen}
        onCancel={() => setIsCncCreateOpen(false)}
        onOk={handleSubmitCreateCnc}
        confirmLoading={createMachineMutation.isPending}
        okText="Tạo máy & Lưu vị trí"
        cancelText="Hủy"
        centered
        width={560}
      >
        <Form form={cncForm} layout="vertical" className="mt-4">
          <div className="grid grid-cols-2 gap-3">
            <Form.Item
              name="machine_code"
              label="Mã máy CNC"
              rules={[
                { required: true, message: 'Vui lòng nhập mã máy CNC!' },
                { pattern: /^[A-Z0-9_-]+$/, message: 'Mã chỉ gồm chữ hoa, số và dấu gạch nối (VD: CNC-05)' },
              ]}
            >
              <Input
                placeholder="Ví dụ: CNC-05"
                className="uppercase"
                onChange={(e) => handleCncCodeChange(e.target.value)}
              />
            </Form.Item>

            <Form.Item
              name="machine_name"
              label="Tên hiển thị máy"
              rules={[{ required: true, message: 'Vui lòng nhập tên máy!' }]}
            >
              <Input placeholder="Ví dụ: Máy Phay CNC 05" />
            </Form.Item>
          </div>

          <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 mb-3 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                  Cấu hình Vị trí Đỗ (1 đến 3 Slots)
                </span>
                <p className="text-[11px] text-slate-500 m-0">
                  Mỗi vị trí gắn với một Node Map KUKA để AMR điều phối phôi vào/ra
                </p>
              </div>

              {createSlots.length < 3 && (
                <Button
                  size="sm"
                  variant="outline"
                  icon={<PlusOutlined />}
                  onClick={handleAddCreateSlot}
                  className="!h-7 !text-xs !rounded-lg text-brand-primary border-brand-primary/40 hover:!bg-brand-primary/10"
                >
                  + Thêm vị trí đỗ
                </Button>
              )}
            </div>

            <div className="space-y-2.5">
              {createSlots.map((slot, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200/80 rounded-lg p-2.5 flex items-center justify-between gap-3 shadow-2xs"
                >
                  <div className="flex items-center gap-2">
                    {renderPosBadge(slot.position_index)}
                    <span className="font-mono text-xs font-bold text-slate-700">
                      {slot.location_code || `POS${slot.position_index}`}
                    </span>
                  </div>

                  <div className="flex-1 max-w-[280px]">
                    <Select
                      size="small"
                      showSearch
                      placeholder={`Chọn Node Map cho POS${slot.position_index}`}
                      value={slot.node_label}
                      onChange={(val) => handleCreateSlotNodeChange(idx, val)}
                      options={nodeOptions}
                      filterOption={(input, option) =>
                        (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
                      }
                      className="w-full text-xs"
                    />
                  </div>

                  {createSlots.length > 1 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={<MinusCircleOutlined className="text-slate-400 hover:text-red-500" />}
                      onClick={() => handleRemoveCreateSlot(idx)}
                      className="!h-7 !w-7 !p-0"
                      title="Xóa vị trí này"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </Form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL 2B: SỬA MÁY CNC (Hỗ trợ cấu hình 1..3 Slots) */}
      {/* ========================================================================= */}
      <Modal
        title={`Chỉnh sửa cấu hình ${editingCnc?.machine_code || ''}`}
        open={!!editingCnc}
        onCancel={() => setEditingCnc(null)}
        onOk={handleSubmitEditCnc}
        confirmLoading={updateMachineMutation.isPending}
        okText="Lưu thay đổi"
        cancelText="Hủy"
        centered
        width={560}
      >
        <Form form={cncEditForm} layout="vertical" className="mt-4">
          <div className="grid grid-cols-2 gap-3">
            <Form.Item
              name="machine_name"
              label="Tên hiển thị máy"
              rules={[{ required: true, message: 'Vui lòng nhập tên máy!' }]}
            >
              <Input placeholder="Ví dụ: Máy Phay CNC 01" />
            </Form.Item>

            <Form.Item name="is_active" label="Trạng thái hoạt động" valuePropName="checked">
              <Switch checkedChildren="Hoạt động" unCheckedChildren="Tạm dừng" />
            </Form.Item>
          </div>

          <div className="border border-slate-200 rounded-xl p-3 bg-slate-50/50 mb-3 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                  Cấu hình Vị trí Đỗ (1 đến 3 Slots)
                </span>
                <p className="text-[11px] text-slate-500 m-0">
                  Cập nhật Node Map hoặc mở rộng vị trí đỗ cho máy
                </p>
              </div>

              {editSlots.length < 3 && (
                <Button
                  size="sm"
                  variant="outline"
                  icon={<PlusOutlined />}
                  onClick={handleAddEditSlot}
                  className="!h-7 !text-xs !rounded-lg text-brand-primary border-brand-primary/40 hover:!bg-brand-primary/10"
                >
                  + Thêm vị trí đỗ
                </Button>
              )}
            </div>

            <div className="space-y-2.5">
              {editSlots.map((slot, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-slate-200/80 rounded-lg p-2.5 flex items-center justify-between gap-3 shadow-2xs"
                >
                  <div className="flex items-center gap-2">
                    {renderPosBadge(slot.position_index)}
                    <span className="font-mono text-xs font-bold text-slate-700">
                      {slot.location_code || `POS${slot.position_index}`}
                    </span>
                  </div>

                  <div className="flex-1 max-w-[280px]">
                    <Select
                      size="small"
                      showSearch
                      placeholder={`Chọn Node Map cho POS${slot.position_index}`}
                      value={slot.node_label}
                      onChange={(val) => handleEditSlotNodeChange(idx, val)}
                      options={nodeOptions}
                      filterOption={(input, option) =>
                        (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
                      }
                      className="w-full text-xs"
                    />
                  </div>

                  {editSlots.length > 1 && (
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={<MinusCircleOutlined className="text-slate-400 hover:text-red-500" />}
                      onClick={() => handleRemoveEditSlot(idx)}
                      className="!h-7 !w-7 !p-0"
                      title="Xóa vị trí này"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </Form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL 3A: THÊM / SỬA SLOT TẨY RỬA */}
      {/* ========================================================================= */}
      <Modal
        title={editingWash ? `Chỉnh sửa '${editingWash.location_code}'` : 'Thêm Slot Khu Tẩy Rửa'}
        open={isWashModalOpen}
        onCancel={() => setIsWashModalOpen(false)}
        onOk={handleSubmitWash}
        confirmLoading={createLocationMutation.isPending || updateLocationMutation.isPending}
        okText={editingWash ? 'Lưu thay đổi' : 'Thêm slot'}
        cancelText="Hủy"
        centered
        width={480}
      >
        <Form form={washForm} layout="vertical" className="mt-4">
          <Form.Item
            name="location_code"
            label="Mã slot tẩy rửa"
            rules={[
              { required: true, message: 'Vui lòng nhập mã slot!' },
              { pattern: /^[A-Z0-9_-]+$/, message: 'Mã chỉ gồm chữ hoa, số và dấu gạch nối (VD: WASH-01)' },
            ]}
          >
            <Input placeholder="Ví dụ: WASH-01" className="uppercase" disabled={!!editingWash} />
          </Form.Item>

          <Form.Item
            name="location_name"
            label="Tên hiển thị slot"
            rules={[{ required: true, message: 'Vui lòng nhập tên slot!' }]}
          >
            <Input placeholder="Ví dụ: Trạm Tẩy Rửa 01" />
          </Form.Item>

          <Form.Item
            name="node_label"
            label="Chọn Node Map KUKA liên kết"
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <Select
              showSearch
              placeholder="Chọn điểm đỗ Node trên Map"
              options={nodeOptions}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          {editingWash && (
            <Form.Item name="is_active" label="Trạng thái hoạt động" valuePropName="checked">
              <Switch checkedChildren="Hoạt động" unCheckedChildren="Tạm dừng" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL 3B: THÊM / SỬA BÃI ĐỆM XE RỖNG */}
      {/* ========================================================================= */}
      <Modal
        title={editingBuffer ? `Chỉnh sửa '${editingBuffer.location_code}'` : 'Thêm Bãi Đệm Xe Rỗng'}
        open={isBufferModalOpen}
        onCancel={() => setIsBufferModalOpen(false)}
        onOk={handleSubmitBuffer}
        confirmLoading={createLocationMutation.isPending || updateLocationMutation.isPending}
        okText={editingBuffer ? 'Lưu thay đổi' : 'Thêm bãi đệm'}
        cancelText="Hủy"
        centered
        width={480}
      >
        <Form form={bufferForm} layout="vertical" className="mt-4">
          <Form.Item
            name="location_code"
            label="Mã bãi đệm"
            rules={[
              { required: true, message: 'Vui lòng nhập mã bãi đệm!' },
              { pattern: /^[A-Z0-9_-]+$/, message: 'Mã chỉ gồm chữ hoa, số và dấu gạch nối (VD: EMPTY-01)' },
            ]}
          >
            <Input placeholder="Ví dụ: EMPTY-01" className="uppercase" disabled={!!editingBuffer} />
          </Form.Item>

          <Form.Item
            name="location_name"
            label="Tên hiển thị bãi đệm"
            rules={[{ required: true, message: 'Vui lòng nhập tên bãi đệm!' }]}
          >
            <Input placeholder="Ví dụ: Bãi Đệm Xe Rỗng 01" />
          </Form.Item>

          <Form.Item
            name="node_label"
            label="Chọn Node Map KUKA liên kết"
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <Select
              showSearch
              placeholder="Chọn điểm đỗ Node trên Map"
              options={nodeOptions}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          {editingBuffer && (
            <Form.Item name="is_active" label="Trạng thái hoạt động" valuePropName="checked">
              <Switch checkedChildren="Hoạt động" unCheckedChildren="Tạm dừng" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
