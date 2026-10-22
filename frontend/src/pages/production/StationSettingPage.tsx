import { useState, useMemo, useCallback } from 'react';
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
  useCreateStationLocation,
  useUpdateStationLocation,
  useDeleteStationLocation,
} from '@/hooks/useStations';
import {
  useCreateMachine,
  useUpdateMachine,
  useDeleteMachine,
} from '@/hooks/useMachines';
import type {
  StationCatalogItem,
  MachineCatalogGroup,
  AvailableMapNode,
} from '@/types/station';
import type { SlotConfigInput } from '@/types/machine';

interface SlotFormItem {
  id?: number;
  position_index: number;
  location_code: string;
  node_label?: string;
  map_x?: number;
  map_y?: number;
}

export default function StationSettingPage() {
  const { data: catalog, isLoading, refetch } = useStationCatalog();
  const { data: availableNodes = [], refetch: refetchNodes } = useAvailableNodes();

  const handleRefreshAll = useCallback(() => {
    refetch();
    refetchNodes();
  }, [refetch, refetchNodes]);

  const createMachineMutation = useCreateMachine();
  const updateMachineMutation = useUpdateMachine();
  const deleteMachineMutation = useDeleteMachine();

  const createLocationMutation = useCreateStationLocation();
  const updateLocationMutation = useUpdateStationLocation();
  const deleteLocationMutation = useDeleteStationLocation();

  // Active Tab: 'raw_material' | 'cnc' | 'washing' | 'empty_buffer'
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

  // 3. Washing
  const [isWashModalOpen, setIsWashModalOpen] = useState(false);
  const [editingWash, setEditingWash] = useState<StationCatalogItem | null>(null);
  const [washForm] = Form.useForm();

  // 4. Empty Buffer
  const [isEmptyBufferModalOpen, setIsEmptyBufferModalOpen] = useState(false);
  const [editingEmptyBuffer, setEditingEmptyBuffer] = useState<StationCatalogItem | null>(null);
  const [emptyBufferForm] = Form.useForm();

  // Realtime in-memory derivation: Quét toàn bộ các vị trí đã gán hiện có trên toàn xưởng từ catalog
  const assignedNodesMap = useMemo(() => {
    const map = new Map<string, { id?: number; name: string; zone: string }>();

    // 1. Raw Materials
    catalog?.raw_materials?.forEach((rm) => {
      const label = rm.node_label || rm.location_label;
      if (label) {
        map.set(String(label), {
          id: rm.id,
          name: rm.location_name || rm.location_code,
          zone: 'Khu Cấp Phôi',
        });
      }
    });

    // 2. CNC Machines and Slots
    catalog?.machines?.forEach((m) => {
      m.slots?.forEach((s) => {
        const label = s.node_label || s.location_label;
        if (label) {
          map.set(String(label), {
            id: s.id,
            name: `${m.machine_code} (POS${s.position_index})`,
            zone: 'Khu Máy CNC',
          });
        }
      });
    });

    // 3. Washing Slots
    catalog?.washing_slots?.forEach((w) => {
      const label = w.node_label || w.location_label;
      if (label) {
        map.set(String(label), {
          id: w.id,
          name: w.location_name || w.location_code,
          zone: 'Khu Tẩy Rửa',
        });
      }
    });

    // 4. Empty Buffers
    const emptyBuffers = catalog?.empty_buffers || [];
    emptyBuffers.forEach((b) => {
      const label = b.node_label || b.location_label;
      if (label) {
        map.set(String(label), {
          id: b.id,
          name: b.location_name || b.location_code,
          zone: 'Bãi Đệm Xe Rỗng',
        });
      }
    });

    return map;
  }, [catalog]);

  // Helper options for map node select: Tự động vô hiệu hóa (xám) node đã gán ở bất kỳ khu vực nào
  const getNodeOptions = useCallback(
    (options?: {
      currentLocationId?: number | null;
      selectedInForm?: (string | undefined)[];
      currentSlotNode?: string;
    }) => {
      const { currentLocationId, selectedInForm = [], currentSlotNode } = options || {};

      return availableNodes.map((n) => {
        const labelStr = String(n.node_label);
        const assignedInfo = assignedNodesMap.get(labelStr);
        const isAssignedInDb = n.is_assigned;

        // Is it assigned to the current entity being edited?
        const isAssignedToSelf = currentLocationId && assignedInfo?.id === currentLocationId;

        // Is it picked by another slot in the current multi-slot CNC form?
        const isPickedByOtherSlotInForm =
          selectedInForm.includes(n.node_label) && n.node_label !== currentSlotNode;

        let isDisabled = false;
        let badge = '[Chưa gán]';

        if (isPickedByOtherSlotInForm) {
          isDisabled = true;
          badge = '[Đang chọn ở vị trí khác trong máy]';
        } else if (assignedInfo) {
          if (isAssignedToSelf) {
            isDisabled = false;
            badge = `[Hiện tại: ${assignedInfo.name}]`;
          } else {
            isDisabled = true;
            badge = `[Đã gán: ${assignedInfo.name} - ${assignedInfo.zone}]`;
          }
        } else if (isAssignedInDb) {
          isDisabled = true;
          badge = `[Đã gán: ${n.assigned_to || 'Khu khác'}]`;
        }

        return {
          value: n.node_label,
          disabled: isDisabled,
          label: `${n.node_number} ${badge}`,
          node: n,
        };
      });
    },
    [availableNodes, assignedNodesMap]
  );

  const nodeOptions = useMemo(() => getNodeOptions(), [getNodeOptions]);
  // =========================================================================
  // HANDLERS: TAB 1 - KHU CẤP PHÔI
  // =========================================================================
  const handleOpenCreateRaw = () => {
    setEditingRaw(null);
    rawForm.resetFields();
    rawForm.setFieldsValue({
      location_name: `VT-0${(catalog?.raw_materials?.length || 0) + 1}`,
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
            location_name: values.location_name.trim(),
            node_label: values.node_label,
            map_x: selectedNode ? selectedNode.map_x : editingRaw.map_x ?? undefined,
            map_y: selectedNode ? selectedNode.map_y : editingRaw.map_y ?? undefined,
          },
        });
        message.success(`Cập nhật ô cấp phôi '${values.location_name}' thành công!`);
      } else {
        await createLocationMutation.mutateAsync({
          location_code: selectedNode?.node_label || values.node_label,
          location_name: values.location_name.trim(),
          location_type: 'RAW_MATERIAL',
          node_label: values.node_label,
          map_x: selectedNode ? selectedNode.map_x : undefined,
          map_y: selectedNode ? selectedNode.map_y : undefined,
          position_index: (catalog?.raw_materials?.length || 0) + 1,
        });
        message.success(`Gán ô cấp phôi '${values.location_name}' (Node ${values.node_label}) thành công!`);
      }
      setIsRawModalOpen(false);
      handleRefreshAll();
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
      handleRefreshAll();
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
      location_code: `${(cncForm.getFieldValue('machine_code') || 'CNC-XX').toUpperCase().trim()}-POS${idx + 1
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
      handleRefreshAll();
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
    });

    const currentSlots: SlotFormItem[] = (m.slots || []).map((s, idx) => ({
      id: s.id,
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
        id: s.id,
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
          slots: slotsPayload,
        },
      });

      message.success(`Cập nhật cấu hình máy '${editingCnc.machine_code}' thành công!`);
      setEditingCnc(null);
      handleRefreshAll();
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
      handleRefreshAll();
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
      location_name: `WASH-0${count}`,
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
          },
        });
        message.success(`Cập nhật slot tẩy rửa '${editingWash.location_code}' thành công!`);
      } else {
        await createLocationMutation.mutateAsync({
          location_code: selectedNode?.node_label || values.node_label,
          location_name: values.location_name.trim(),
          location_type: 'WASHING_SLOT',
          node_label: values.node_label,
          map_x: selectedNode ? selectedNode.map_x : undefined,
          map_y: selectedNode ? selectedNode.map_y : undefined,
          position_index: (catalog?.washing_slots?.length || 0) + 1,
        });
        message.success(`Gán slot tẩy rửa '${values.location_name}' (Node ${values.node_label}) thành công!`);
      }
      setIsWashModalOpen(false);
      handleRefreshAll();
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
      handleRefreshAll();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || 'Không thể xóa slot tẩy rửa');
    }
  };

  // Empty Buffer Handlers
  const emptyBufferList = catalog?.empty_buffers || [];

  const handleOpenCreateEmptyBuffer = () => {
    setEditingEmptyBuffer(null);
    emptyBufferForm.resetFields();
    const count = emptyBufferList.length + 1;
    emptyBufferForm.setFieldsValue({
      location_name: `EMPTY-0${count}`,
    });
    setIsEmptyBufferModalOpen(true);
  };

  const handleOpenEditEmptyBuffer = (item: StationCatalogItem) => {
    setEditingEmptyBuffer(item);
    emptyBufferForm.resetFields();
    emptyBufferForm.setFieldsValue({
      location_code: item.location_code,
      location_name: item.location_name || '',
      node_label: item.node_label || undefined,
      is_active: item.is_active,
    });
    setIsEmptyBufferModalOpen(true);
  };

  const handleSubmitEmptyBuffer = async () => {
    try {
      const values = await emptyBufferForm.validateFields();
      const selectedNode = availableNodes.find((n) => n.node_label === values.node_label);

      if (editingEmptyBuffer) {
        await updateLocationMutation.mutateAsync({
          id: editingEmptyBuffer.id,
          data: {
            location_name: values.location_name,
            node_label: values.node_label,
            map_x: selectedNode ? selectedNode.map_x : editingEmptyBuffer.map_x ?? undefined,
            map_y: selectedNode ? selectedNode.map_y : editingEmptyBuffer.map_y ?? undefined,
          },
        });
        message.success(`Cập nhật bãi đệm '${editingEmptyBuffer.location_code}' thành công!`);
      } else {
        await createLocationMutation.mutateAsync({
          location_code: selectedNode?.node_label || values.node_label,
          location_name: values.location_name.trim(),
          location_type: 'EMPTY_CART_BUFFER',
          node_label: values.node_label,
          map_x: selectedNode ? selectedNode.map_x : undefined,
          map_y: selectedNode ? selectedNode.map_y : undefined,
          position_index: emptyBufferList.length + 1,
        });
        message.success(`Gán bãi đệm '${values.location_name}' (Node ${values.node_label}) thành công!`);
      }
      setIsEmptyBufferModalOpen(false);
      handleRefreshAll();
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail);
      } else if (!err?.errorFields) {
        message.error('Không thể lưu bãi đệm xe rỗng');
      }
    }
  };

  const handleDeleteEmptyBuffer = async (id: number, code: string) => {
    try {
      await deleteLocationMutation.mutateAsync(id);
      message.success(`Đã xóa bãi đệm '${code}'`);
      handleRefreshAll();
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
                        title: 'Tên Đặt Nghiệp Vụ',
                        dataIndex: 'location_name',
                        key: 'location_name',
                        width: 180,
                        render: (text: string) => (
                          <span className="font-mono font-bold text-amber-900 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200">
                            {text || '—'}
                          </span>
                        ),
                      },
                      {
                        title: 'Node Bản Đồ',
                        key: 'location_label',
                        width: 140,
                        render: (_: any, record: StationCatalogItem) => (
                          <Tag color="cyan" className="!font-bold !m-0 font-mono">
                            Node {record.location_label || record.node_label || '--'}
                          </Tag>
                        ),
                      },
                      {
                        title: 'Mã Node KUKA (UUID Fleet)',
                        dataIndex: 'location_code',
                        key: 'location_code',
                        render: (text: string) => (
                          <span className="font-mono text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                            {text}
                          </span>
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
            key: 'washing',
            label: (
              <span className="flex items-center gap-2">
                <ExperimentOutlined className="text-emerald-600 text-base" />
                <span>Khu Tẩy Rửa ({catalog?.washing_slots?.length || 0})</span>
              </span>
            ),
            children: (
              <div className="space-y-4">
                <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <InfoCircleOutlined className="text-emerald-600 text-xl shrink-0" />
                    <div className="text-xs text-emerald-900 leading-relaxed">
                      <span className="font-bold">Khu Tẩy Rửa:</span> Trạm tẩy rửa tiếp nhận xe phôi sau khi hoàn thành công đoạn CNC cuối cùng. Xe sau khi làm sạch sẽ được dỡ phôi và đưa sang bãi đệm xe rỗng.
                    </div>
                  </div>
                  <Button
                    onClick={handleOpenCreateWash}
                    icon={<PlusOutlined />}
                    className="!bg-emerald-600 hover:!bg-emerald-700 !border-none !text-white !h-9 !px-4 !rounded-lg font-semibold shrink-0"
                  >
                    Thêm Slot Tẩy Rửa
                  </Button>
                </div>

                <Card className="rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                  <Table
                    loading={isLoading}
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
            ),
          },
          {
            key: 'empty_buffer',
            label: (
              <span className="flex items-center gap-2">
                <CarOutlined className="text-blue-600 text-base" />
                <span>Bãi Đệm Xe Rỗng ({emptyBufferList.length})</span>
              </span>
            ),
            children: (
              <div className="space-y-4">
                <div className="bg-blue-50/60 border border-blue-200/80 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <InfoCircleOutlined className="text-blue-600 text-xl shrink-0" />
                    <div className="text-xs text-blue-900 leading-relaxed">
                      <span className="font-bold">Bãi Đệm Xe Rỗng (Empty Cart Buffer):</span> Vị trí tập kết các xe Rack rỗng (đã dỡ sạch chi tiết). Khi khu Cấp Phôi hoặc các trạm phát sinh nhu cầu, AMR sẽ đến bãi đệm này lấy xe rỗng đi phục vụ.
                    </div>
                  </div>
                  <Button
                    onClick={handleOpenCreateEmptyBuffer}
                    icon={<PlusOutlined />}
                    className="!bg-blue-600 hover:!bg-blue-700 !border-none !text-white !h-9 !px-4 !rounded-lg font-semibold shrink-0"
                  >
                    Thêm Bãi Đệm
                  </Button>
                </div>

                <Card className="rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
                  <Table
                    loading={isLoading}
                    dataSource={emptyBufferList}
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
                              onClick={() => handleOpenEditEmptyBuffer(record)}
                              className="!h-8 !px-2 text-slate-600 hover:text-blue-600"
                            />
                            <Popconfirm
                              title="Xóa bãi đệm xe rỗng này?"
                              okText="Xóa"
                              cancelText="Hủy"
                              okButtonProps={{ danger: true }}
                              onConfirm={() => handleDeleteEmptyBuffer(record.id, record.location_code)}
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
            name="node_label"
            label="Chọn Node Bản Đồ KUKA"
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <Select
              showSearch
              placeholder="Chọn điểm đỗ Node trên Map (chưa gán)"
              options={getNodeOptions({ currentLocationId: editingRaw?.id })}
              disabled={!!editingRaw}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          <Form.Item
            name="location_name"
            label="Tên Đặt Nghiệp Vụ (Hiển thị PDA / Web)"
            rules={[{ required: true, message: 'Vui lòng nhập tên đặt cho ô!' }]}
          >
            <Input placeholder="Ví dụ: VT-01, Ô Cấp Phôi 1..." />
          </Form.Item>


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
                      options={getNodeOptions({
                        selectedInForm: createSlots.map((s) => s.node_label),
                        currentSlotNode: slot.node_label,
                      })}
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
                      options={getNodeOptions({
                        currentLocationId: slot.id,
                        selectedInForm: editSlots.map((s) => s.node_label),
                        currentSlotNode: slot.node_label,
                      })}
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
            name="node_label"
            label="Chọn Node Bản Đồ KUKA"
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <Select
              showSearch
              placeholder="Chọn điểm đỗ Node trên Map (chưa gán)"
              options={getNodeOptions({ currentLocationId: editingWash?.id })}
              disabled={!!editingWash}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          <Form.Item
            name="location_name"
            label="Tên Đặt Nghiệp Vụ (Hiển thị PDA / Web)"
            rules={[{ required: true, message: 'Vui lòng nhập tên slot!' }]}
          >
            <Input placeholder="Ví dụ: WASH-01, Bồn Rửa 1..." />
          </Form.Item>


        </Form>
      </Modal>

      {/* ========================================================================= */}
      {/* MODAL 4: THÊM / SỬA BÃI ĐỆM XE RỖNG */}
      {/* ========================================================================= */}
      <Modal
        title={editingEmptyBuffer ? `Chỉnh sửa '${editingEmptyBuffer.location_code}'` : 'Thêm Bãi Đệm Xe Rỗng'}
        open={isEmptyBufferModalOpen}
        onCancel={() => setIsEmptyBufferModalOpen(false)}
        onOk={handleSubmitEmptyBuffer}
        confirmLoading={createLocationMutation.isPending || updateLocationMutation.isPending}
        okText={editingEmptyBuffer ? 'Lưu thay đổi' : 'Thêm bãi đệm'}
        cancelText="Hủy"
        centered
        width={480}
      >
        <Form form={emptyBufferForm} layout="vertical" className="mt-4">
          <Form.Item
            name="node_label"
            label="Chọn Node Bản Đồ KUKA"
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <Select
              showSearch
              placeholder="Chọn điểm đỗ Node trên Map (chưa gán)"
              options={getNodeOptions({ currentLocationId: editingEmptyBuffer?.id })}
              disabled={!!editingEmptyBuffer}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          <Form.Item
            name="location_name"
            label="Tên Đặt Nghiệp Vụ (Hiển thị PDA / Web)"
            rules={[{ required: true, message: 'Vui lòng nhập tên bãi đệm!' }]}
          >
            <Input placeholder="Ví dụ: EMPTY-01, Bãi Đệm 1..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
