import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Button,
  Modal,
  Form,
  Input,
  Select,
  TextArea,
  message,
  Space,
  Table,
} from '@/components/ui';
import { Tag, Switch, Tooltip, Alert, Radio } from 'antd';
import {
  ReloadOutlined,
  DeleteOutlined,
  EnvironmentOutlined,
  SearchOutlined,
  InboxOutlined,
  LockOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  SwapRightOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import Hero from '@/components/shared/Hero';
import {
  getProductionRacksApi,
  removeProductionRackApi,
  syncProductionRackBypassApi,
  type RackManagementItem,
  type RackSyncBypassMode,
} from '@/api/rackManagement';
import {
  getProductionRouteDetailApi,
  getProductionRoutesApi,
} from '@/api/productionRoute';
import { useAvailableNodes, useStationCatalog } from '@/hooks/useStations';
import type { AvailableMapNode, StationCatalogItem } from '@/types/station';
import type { ProductionRoute } from '@/types/productionRoute';
import NodeSelectWithMap from '@/pages/components/stationSetting/NodeSelectWithMap';
import { useMapPicker } from '@/pages/components/stationSetting/useMapPicker';
import { useStationNodes } from '@/pages/components/stationSetting/useStationNodes';
import { MapNodePickerModal } from '@/pages/components/MapNodePickerModal';

type BypassRouteContext = {
  routeId: number;
  routeCode: string;
  /** machine_code → stage_level (S) trong route_step_machine */
  machineStageByCode: Map<string, number>;
  /** stage_level của bước is_final_cnc_step */
  finalStage: number;
};

function buildBypassRouteContext(route: ProductionRoute): BypassRouteContext {
  const machineStageByCode = new Map<string, number>();
  let finalStage = 0;
  for (const step of route.steps || []) {
    if (step.is_final_cnc_step) {
      finalStage = Math.max(finalStage, step.stage_level);
    }
    for (const code of step.allowed_machines || []) {
      const prev = machineStageByCode.get(code) ?? 0;
      machineStageByCode.set(code, Math.max(prev, step.stage_level));
    }
  }
  if (!finalStage) {
    finalStage = Math.max(0, ...(route.steps || []).map((s) => s.stage_level), 0);
  }
  return {
    routeId: route.id,
    routeCode: route.route_code,
    machineStageByCode,
    finalStage,
  };
}

function deriveStageFromLocation(
  loc: StationCatalogItem,
  routeCtx: BypassRouteContext | null,
): number | null {
  if (loc.location_type === 'RAW_MATERIAL') return 0;
  if (!routeCtx) return null;
  if (loc.location_type === 'WASHING_SLOT') {
    return routeCtx.finalStage > 0 ? routeCtx.finalStage : null;
  }
  if (loc.location_type === 'CNC_SLOT') {
    if (!loc.machine_code) return null;
    return routeCtx.machineStageByCode.has(loc.machine_code)
      ? routeCtx.machineStageByCode.get(loc.machine_code)!
      : null;
  }
  return null;
}

function isLocationOnRoute(
  loc: StationCatalogItem,
  routeCtx: BypassRouteContext | null,
  mode: RackSyncBypassMode | undefined,
): boolean {
  if (mode === 'DISPATCH_TO_WASH') {
    return loc.location_type === 'WASHING_SLOT' && !!routeCtx && routeCtx.finalStage > 0;
  }
  if (loc.location_type === 'RAW_MATERIAL') return true;
  if (loc.location_type === 'WASHING_SLOT') {
    return !!routeCtx && routeCtx.finalStage > 0;
  }
  if (loc.location_type === 'CNC_SLOT') {
    return !!loc.machine_code && !!routeCtx?.machineStageByCode.has(loc.machine_code);
  }
  return false;
}

const toNodeKey = (value?: string | number | null) => String(value ?? '').toLowerCase();

function findStationByMapNode(
  node: AvailableMapNode,
  stations: Array<StationCatalogItem & { groupLabel?: string }>,
) {
  const keys = [toNodeKey(node.node_label), toNodeKey(node.node_number)];
  return stations.find((loc) => {
    const candidates = [
      toNodeKey(loc.location_label),
      toNodeKey(loc.node_label),
      toNodeKey(loc.location_code),
    ];
    return candidates.some(
      (c) =>
        c &&
        (keys.includes(c) ||
          keys.some((k) => k && (c.endsWith(`-${k}`) || c.endsWith(k)))),
    );
  });
}

const AREA_LABELS: Record<string, { label: string; color: string }> = {
  RAW_MATERIAL: { label: 'Khu Nguyên Liệu', color: 'blue' },
  CNC_SLOT: { label: 'Máy CNC', color: 'purple' },
  WASHING_SLOT: { label: 'Khu Tẩy Rửa', color: 'cyan' },
  EMPTY_CART_BUFFER: { label: 'Bãi Xe Trống', color: 'default' },
};

export default function RackManagementPage() {
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState('');
  const [areaFilter, setAreaFilter] = useState<string>('ALL');
  const [includeInactive, setIncludeInactive] = useState(false);

  // Modal Đồng bộ bypass (vị trí + stage + note)
  const [editingRack, setEditingRack] = useState<RackManagementItem | null>(null);
  const [updateErrorMsg, setUpdateErrorMsg] = useState<string | null>(null);
  const [locationForm] = Form.useForm<{
    mode: RackSyncBypassMode;
    location_id?: number;
    note: string;
  }>();
  const bypassMode = Form.useWatch('mode', locationForm) as RackSyncBypassMode | undefined;

  useEffect(() => {
    if (!editingRack) return;
    locationForm.setFieldValue('location_id', undefined);
  }, [bypassMode, editingRack, locationForm]);

  const { data: activeRouteDetail } = useQuery({
    queryKey: ['production-route-for-bypass', editingRack?.item_id],
    enabled: Boolean(editingRack?.item_id),
    queryFn: async () => {
      const itemId = editingRack!.item_id!;
      const routes = await getProductionRoutesApi({ item_id: itemId, is_active: true });
      const active = routes[0];
      if (!active) return null;
      return getProductionRouteDetailApi(active.id);
    },
  });

  const bypassRouteCtx = useMemo(
    () => (activeRouteDetail ? buildBypassRouteContext(activeRouteDetail) : null),
    [activeRouteDetail],
  );

  // Modal Xóa Rack (containerOut)
  const [deletingRack, setDeletingRack] = useState<RackManagementItem | null>(null);
  const [deleteErrorMsg, setDeleteErrorMsg] = useState<string | null>(null);

  const {
    data: racks = [],
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['production-racks', { includeInactive }],
    queryFn: () => getProductionRacksApi({ include_inactive: includeInactive }),
    refetchInterval: 10000,
  });

  const { data: stationCatalog } = useStationCatalog();
  const { data: availableNodes = [] } = useAvailableNodes();
  const { assignedNodesMap } = useStationNodes(stationCatalog, availableNodes);
  const { mapPicker, openMapPicker, closeMapPicker } = useMapPicker();

  // Gom các vị trí trạm sản xuất (Nguyên liệu, Máy CNC, Tẩy rửa — không cho phép chuyển vào Bãi xe trống)
  const allStationLocations = useMemo(() => {
    if (!stationCatalog) return [];
    const list: Array<StationCatalogItem & { groupLabel: string }> = [];

    for (const raw of stationCatalog.raw_materials || []) {
      list.push({ ...raw, groupLabel: '1. Khu Nguyên Liệu (RAW_MATERIAL - Phôi thô Lv 0)' });
    }
    for (const machine of stationCatalog.machines || []) {
      for (const slot of machine.slots || []) {
        list.push({
          ...slot,
          machine_code: machine.machine_code,
          groupLabel: `2. Máy CNC (${machine.machine_code})`,
        });
      }
    }
    for (const wash of stationCatalog.washing_slots || []) {
      list.push({ ...wash, groupLabel: '3. Khu Tẩy Rửa (WASHING_SLOT - Đã xong CNC cuối)' });
    }
    return list;
  }, [stationCatalog]);

  // Bản đồ vị trí đang có rack nào đỗ (để hiển thị cảnh báo trực quan trong dropdown)
  const occupiedByLocationId = useMemo(() => {
    const map = new Map<number, string>();
    for (const r of racks) {
      if (r.is_active && r.location_id != null) {
        map.set(r.location_id, r.container_code);
      }
    }
    return map;
  }, [racks]);

  // Bypass: chỉ hiện node thuộc cùng route (CNC qua route_step_machine; wash = final step).
  const bypassLocationSelectOptions = useMemo(() => {
    const groups = new Map<
      string,
      Array<{ value: string; label: string; disabled?: boolean }>
    >();

    const washOnly = bypassMode === 'DISPATCH_TO_WASH';

    for (const loc of allStationLocations) {
      if (washOnly && loc.location_type !== 'WASHING_SLOT') continue;

      const onRoute = isLocationOnRoute(loc, bypassRouteCtx, bypassMode);
      const derivedStage = deriveStageFromLocation(loc, bypassRouteCtx);
      const occupant = occupiedByLocationId.get(loc.id);
      const isOccupiedByOther =
        Boolean(occupant) && occupant !== editingRack?.container_code;
      const isSameCurrentLoc =
        Boolean(editingRack?.location_id) && loc.id === editingRack?.location_id;

      const displayLabel = loc.location_name || loc.location_code;
      const nodeHint = loc.location_label || loc.node_label || loc.location_code;

      let statusText = ' [Trống]';
      if (!onRoute) {
        statusText = ' [Ngoài quy trình model]';
      } else if (derivedStage != null) {
        statusText = ` [→ Lv ${derivedStage}]`;
      }
      if (isSameCurrentLoc) {
        statusText += ' [Hiện tại]';
      } else if (isOccupiedByOther) {
        statusText += ` [Có rack: ${occupant}]`;
      }

      const arr = groups.get(loc.groupLabel) || [];
      arr.push({
        value: String(loc.id),
        label: `${displayLabel} (${nodeHint})${statusText}`,
        disabled:
          !onRoute ||
          isOccupiedByOther ||
          (bypassMode === 'SYNC_PHYSICAL' && isSameCurrentLoc),
      });
      groups.set(loc.groupLabel, arr);
    }

    return Array.from(groups.entries()).map(([label, options]) => ({
      label,
      options,
    }));
  }, [
    allStationLocations,
    occupiedByLocationId,
    editingRack,
    bypassMode,
    bypassRouteCtx,
  ]);

  const selectedBypassLocationId = Form.useWatch('location_id', locationForm) as
    | number
    | undefined;

  const selectedBypassNodeLabel = useMemo(() => {
    if (selectedBypassLocationId == null) return undefined;
    const loc = allStationLocations.find((l) => l.id === selectedBypassLocationId);
    return loc?.location_label || loc?.node_label || loc?.location_code || undefined;
  }, [allStationLocations, selectedBypassLocationId]);

  const openBypassMapPicker = () => {
    openMapPicker({
      title:
        bypassMode === 'DISPATCH_TO_WASH'
          ? 'Chọn ô rửa trên bản đồ KUKA'
          : 'Chọn vị trí thực tế trên bản đồ KUKA',
      currentSelectedNodeLabel: selectedBypassNodeLabel,
      currentLocationId: editingRack?.location_id,
      onSelect: (node) => {
        const matched = findStationByMapNode(node, allStationLocations);
        if (!matched) {
          message.error(
            `Node ${node.node_number} chưa gắn trạm sản xuất (NL/CNC/Rửa).`,
          );
          return;
        }
        if (!isLocationOnRoute(matched, bypassRouteCtx, bypassMode)) {
          message.error(
            `Node/vị trí '${matched.location_name || matched.location_code}' không thuộc quy trình ` +
              `${bypassRouteCtx?.routeCode || 'của model'} — không thể chọn.`,
          );
          return;
        }
        if (bypassMode === 'DISPATCH_TO_WASH' && matched.location_type !== 'WASHING_SLOT') {
          message.error('Mode DISPATCH_TO_WASH chỉ nhận ô WASHING_SLOT.');
          return;
        }
        const occupant = occupiedByLocationId.get(matched.id);
        if (occupant && occupant !== editingRack?.container_code) {
          message.error(
            `Vị trí '${matched.location_name || matched.location_code}' đang có rack ${occupant}.`,
          );
          return;
        }
        locationForm.setFieldValue('location_id', matched.id);
        closeMapPicker();
      },
    });
  };

  const selectedBypassLocation = useMemo(() => {
    if (selectedBypassLocationId == null) return null;
    return allStationLocations.find((l) => l.id === selectedBypassLocationId) || null;
  }, [allStationLocations, selectedBypassLocationId]);

  const derivedBypassStage = useMemo(() => {
    if (!selectedBypassLocation) {
      if (bypassMode === 'DISPATCH_TO_WASH' && bypassRouteCtx) {
        return bypassRouteCtx.finalStage > 0 ? bypassRouteCtx.finalStage : null;
      }
      return null;
    }
    return deriveStageFromLocation(selectedBypassLocation, bypassRouteCtx);
  }, [selectedBypassLocation, bypassRouteCtx, bypassMode]);

  const filteredRacks = useMemo(() => {
    return racks.filter((r) => {
      if (areaFilter !== 'ALL') {
        if (areaFilter === 'IN_TRANSIT') {
          if (!r.is_locked && !r.active_request_code) return false;
        } else if (r.location_type !== areaFilter) {
          return false;
        }
      }
      if (searchText.trim()) {
        const kw = searchText.trim().toLowerCase();
        const matchCode = (r.container_code || '').toLowerCase().includes(kw);
        const matchLoc =
          (r.location_name || '').toLowerCase().includes(kw) ||
          (r.location_code || '').toLowerCase().includes(kw) ||
          (r.location_label || '').toLowerCase().includes(kw);
        const matchModel =
          (r.item_sku || '').toLowerCase().includes(kw) ||
          (r.item_name || '').toLowerCase().includes(kw);
        if (!matchCode && !matchLoc && !matchModel) return false;
      }
      return true;
    });
  }, [racks, areaFilter, searchText]);

  const stats = useMemo(() => {
    const active = racks.filter((r) => r.is_active);
    return {
      totalActive: active.length,
      rawCount: active.filter((r) => r.location_type === 'RAW_MATERIAL').length,
      cncCount: active.filter((r) => r.location_type === 'CNC_SLOT').length,
      washCount: active.filter((r) => r.location_type === 'WASHING_SLOT').length,
      lockedCount: active.filter((r) => !r.can_modify).length,
    };
  }, [racks]);

  const removeMutation = useMutation({
    mutationFn: (rackId: number) => removeProductionRackApi(rackId),
    onSuccess: (res) => {
      message.success(res.message || 'Đã xóa Rack thành công');
      setDeletingRack(null);
      setDeleteErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ['production-racks'] });
    },
    onError: (err: any) => {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Không thể xóa Rack do KUKA Fleet từ chối hoặc mất kết nối.';
      setDeleteErrorMsg(detail);
      message.error(detail);
    },
  });

  const syncBypassMutation = useMutation({
    mutationFn: ({
      rackId,
      payload,
    }: {
      rackId: number;
      payload: {
        mode: RackSyncBypassMode;
        note: string;
        location_id?: number;
        current_stage_level?: number;
      };
    }) => syncProductionRackBypassApi(rackId, payload),
    onSuccess: (res) => {
      message.success(res.message || 'Đã đồng bộ bypass Rack thành công');
      setEditingRack(null);
      setUpdateErrorMsg(null);
      locationForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['production-racks'] });
    },
    onError: (err: any) => {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Đồng bộ bypass thất bại. Chọn vị trí khác hoặc thử lại.';
      setUpdateErrorMsg(detail);
      message.error(detail);
    },
  });

  const openEditLocationModal = (rack: RackManagementItem) => {
    setEditingRack(rack);
    setUpdateErrorMsg(null);
    locationForm.setFieldsValue({
      mode: 'SYNC_PHYSICAL',
      note: '',
      location_id: undefined,
    });
  };

  const handleConfirmUpdateLocation = async () => {
    if (!editingRack) return;
    setUpdateErrorMsg(null);
    try {
      const values = await locationForm.validateFields();
      const note = (values.note || '').trim();

      if (values.mode === 'SYNC_PHYSICAL') {
        if (values.location_id == null) {
          message.error('Chọn vị trí/node thực tế (thuộc quy trình model).');
          return;
        }
        const loc = allStationLocations.find((l) => l.id === values.location_id);
        if (!loc || !isLocationOnRoute(loc, bypassRouteCtx, values.mode)) {
          message.error('Vị trí chọn không thuộc quy trình của model trên rack.');
          return;
        }
        const stage = deriveStageFromLocation(loc, bypassRouteCtx);
        if (stage == null) {
          message.error('Không suy được stage từ vị trí đã chọn.');
          return;
        }
        syncBypassMutation.mutate({
          rackId: editingRack.id,
          payload: {
            mode: values.mode,
            note,
            location_id: values.location_id,
            current_stage_level: stage,
          },
        });
        return;
      }

      // DISPATCH_TO_WASH: stage = final is_final_cnc_step
      if (!bypassRouteCtx || bypassRouteCtx.finalStage <= 0) {
        message.error('Model chưa có bước CNC cuối (is_final_cnc_step) trong route.');
        return;
      }
      if (values.location_id != null) {
        const loc = allStationLocations.find((l) => l.id === values.location_id);
        if (!loc || loc.location_type !== 'WASHING_SLOT') {
          message.error('Ô ưu tiên phải là WASHING_SLOT thuộc quy trình.');
          return;
        }
      }
      syncBypassMutation.mutate({
        rackId: editingRack.id,
        payload: {
          mode: values.mode,
          note,
          location_id: values.location_id,
          current_stage_level: bypassRouteCtx.finalStage,
        },
      });
    } catch {
      // form validation error
    }
  };

  const openDeleteModal = (rack: RackManagementItem) => {
    setDeletingRack(rack);
    setDeleteErrorMsg(null);
  };

  const columns = [
    {
      title: 'Mã Rack (Container)',
      dataIndex: 'container_code',
      key: 'container_code',
      width: 190,
      render: (code: string, record: RackManagementItem) => (
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-bold text-slate-900 bg-slate-100 px-2.5 py-0.5 rounded border border-slate-300">
              {code}
            </span>
            {!record.is_active && (
              <Tag color="default" className="m-0 text-[11px]">
                Đã thu hồi
              </Tag>
            )}
          </div>
          <div className="text-[11px] text-slate-500">
            {record.fleet_registered ? (
              <span className="text-emerald-600 font-medium">
                ● Đã đăng ký trên Fleet
              </span>
            ) : (
              <span className="text-slate-400">○ Chưa đăng ký Fleet</span>
            )}
          </div>
        </div>
      ),
    },
    {
      title: 'Vị trí hiện tại',
      key: 'location',
      width: 260,
      render: (_: unknown, record: RackManagementItem) => {
        const areaInfo = record.location_type
          ? AREA_LABELS[record.location_type] || {
              label: record.location_type,
              color: 'default',
            }
          : null;

        if (!record.location_id && record.is_locked) {
          return (
            <div className="flex flex-col gap-1">
              <Tag color="processing" className="w-fit m-0">
                Đang trên lưng AMR
              </Tag>
              {record.destination_location_name && (
                <span className="text-xs text-blue-600 font-medium">
                  <SwapRightOutlined className="mr-1" />
                  Đích: {record.destination_location_name}
                </span>
              )}
            </div>
          );
        }

        if (!record.location_id) {
          return <span className="text-xs text-slate-400 italic">Không có vị trí (Bãi trống)</span>;
        }

        return (
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-semibold text-slate-800 text-sm">
                {record.location_name || record.location_code}
              </span>
              {areaInfo && (
                <Tag color={areaInfo.color} className="m-0 text-[11px]">
                  {areaInfo.label}
                </Tag>
              )}
            </div>
            <div className="text-xs text-slate-500 font-mono">
              Node: {record.location_label || record.location_code}
            </div>
            {record.destination_location_name && (
              <div className="text-xs text-amber-600 font-medium">
                <SwapRightOutlined className="mr-1" />
                Đang điều tới: {record.destination_location_name}
              </div>
            )}
          </div>
        );
      },
    },
    {
      title: 'Model & Số lượng',
      key: 'model',
      width: 220,
      render: (_: unknown, record: RackManagementItem) => (
        <div className="flex flex-col gap-0.5">
          {record.item_name ? (
            <>
              <span className="font-semibold text-slate-800 text-sm">
                {record.item_name}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                SKU: {record.item_sku} • SL:{' '}
                <strong className="text-slate-700">{record.quantity}</strong> phôi
              </span>
            </>
          ) : (
            <span className="text-xs text-slate-400 italic">Chưa gán Model</span>
          )}
        </div>
      ),
    },
    {
      title: 'Công đoạn',
      dataIndex: 'current_stage_level',
      key: 'current_stage_level',
      width: 140,
      render: (level: number, record: RackManagementItem) => {
        if (!record.is_active || record.status === 'empty') {
          return <Tag color="default">Xe rỗng</Tag>;
        }
        if (level === 0) {
          return <Tag color="blue">Phôi thô (Lv 0)</Tag>;
        }
        return <Tag color="geekblue">Hoàn thành Lv {level}</Tag>;
      },
    },
    {
      title: 'Trạng thái',
      key: 'status',
      width: 210,
      render: (_: unknown, record: RackManagementItem) => {
        if (record.is_locked) {
          return (
            <div className="flex flex-col gap-1">
              <Tag icon={<LockOutlined />} color="warning" className="w-fit m-0">
                Đang khóa bởi AMR
              </Tag>
              {record.locked_by_mission_code && (
                <span className="text-[11px] font-mono text-amber-700">
                  {record.locked_by_mission_code}
                </span>
              )}
            </div>
          );
        }
        if (record.active_request_code) {
          return (
            <div className="flex flex-col gap-1">
              <Tag icon={<ClockCircleOutlined />} color="processing" className="w-fit m-0">
                Đang xếp hàng điều xe
              </Tag>
              <span className="text-[11px] font-mono text-blue-700">
                {record.active_request_code} ({record.active_request_status})
              </span>
            </div>
          );
        }
        if (record.status === 'out_failed') {
          return (
            <Tooltip title="AMR đã hạ xe tại bãi đệm nhưng lệnh xóa xe (containerOut) trên KUKA Fleet bị lỗi. Bạn có thể bấm Xóa Rack tại đây để gửi lại lệnh xóa.">
              <Tag icon={<WarningOutlined />} color="error" className="w-fit m-0">
                Lỗi xóa trên Fleet
              </Tag>
            </Tooltip>
          );
        }
        if (!record.is_active || record.status === 'empty') {
          return (
            <Tag color="default" className="w-fit m-0">
              Đã thu hồi (Trống)
            </Tag>
          );
        }
        return (
          <Tag icon={<CheckCircleOutlined />} color="success" className="w-fit m-0">
            Sẵn sàng ({record.status})
          </Tag>
        );
      },
    },
    {
      title: 'Cập nhật lúc',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 155,
      render: (val: string | null) =>
        val ? (
          <span className="text-xs text-slate-600">
            {new Date(val).toLocaleString('vi-VN', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              day: '2-digit',
              month: '2-digit',
            })}
          </span>
        ) : (
          <span className="text-xs text-slate-400">--</span>
        ),
    },
    {
      title: 'Thao tác',
      key: 'actions',
      width: 220,
      fixed: 'right' as const,
      render: (_: unknown, record: RackManagementItem) => {
        const deleteDisabled = !record.can_modify;
        const deleteTooltip = record.block_reason || undefined;
        const relocateDisabled = !(record.can_relocate ?? record.can_modify);
        const relocateTooltip =
          record.relocate_block_reason || record.block_reason || undefined;

        return (
          <Space size="small">
            <Tooltip title={relocateTooltip}>
              <span>
                <Button
                  size="small"
                  icon={<EnvironmentOutlined />}
                  disabled={relocateDisabled}
                  onClick={() => openEditLocationModal(record)}
                >
                  Đồng bộ bypass
                </Button>
              </span>
            </Tooltip>
            <Tooltip title={deleteTooltip}>
              <span>
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  disabled={deleteDisabled}
                  onClick={() => openDeleteModal(record)}
                >
                  Xóa Rack
                </Button>
              </span>
            </Tooltip>
          </Space>
        );
      },
    },
  ];

  return (
    <div className="space-y-6 p-4 md:p-6">
      <Hero
        title="Quản lý Container / Rack"
        subtitle="Kiểm soát danh sách xe phôi (Rack), cập nhật vị trí thực tế và thu hồi Rack (containerQuery → containerOut) đồng bộ với KUKA Fleet."
      />

      {/* Thống kê nhanh */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Card className="p-3.5 border border-slate-200/80 shadow-xs">
          <div className="text-xs text-slate-500 font-medium">Tổng Rack đang hoạt động</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">{stats.totalActive}</div>
        </Card>
        <Card className="p-3.5 border border-blue-200/80 bg-blue-50/30 shadow-xs">
          <div className="text-xs text-blue-600 font-medium">Tại Khu Nguyên Liệu</div>
          <div className="mt-1 text-2xl font-bold text-blue-700">{stats.rawCount}</div>
        </Card>
        <Card className="p-3.5 border border-purple-200/80 bg-purple-50/30 shadow-xs">
          <div className="text-xs text-purple-600 font-medium">Tại Máy CNC</div>
          <div className="mt-1 text-2xl font-bold text-purple-700">{stats.cncCount}</div>
        </Card>
        <Card className="p-3.5 border border-cyan-200/80 bg-cyan-50/30 shadow-xs">
          <div className="text-xs text-cyan-600 font-medium">Tại Khu Tẩy Rửa</div>
          <div className="mt-1 text-2xl font-bold text-cyan-700">{stats.washCount}</div>
        </Card>
        <Card className="p-3.5 border border-amber-200/80 bg-amber-50/30 shadow-xs">
          <div className="text-xs text-amber-600 font-medium">Đang khóa / Chờ điều xe</div>
          <div className="mt-1 text-2xl font-bold text-amber-700">{stats.lockedCount}</div>
        </Card>
      </div>

      {/* Bộ lọc & Thanh công cụ */}
      <Card className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-4">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Tìm theo mã Rack, vị trí, Model..."
              prefix={<SearchOutlined className="text-slate-400" />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              className="w-full sm:w-72"
            />
            <Select
              value={areaFilter}
              onChange={(val) => setAreaFilter(val)}
              className="w-full sm:w-52"
              options={[
                { value: 'ALL', label: 'Tất cả khu vực' },
                { value: 'RAW_MATERIAL', label: 'Khu Nguyên Liệu' },
                { value: 'CNC_SLOT', label: 'Trạm Máy CNC' },
                { value: 'WASHING_SLOT', label: 'Khu Tẩy Rửa' },
                { value: 'EMPTY_CART_BUFFER', label: 'Bãi Xe Trống' },
                { value: 'IN_TRANSIT', label: 'Đang khóa / Hàng đợi' },
              ]}
            />
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
              <Switch
                size="small"
                checked={includeInactive}
                onChange={(checked) => setIncludeInactive(checked)}
              />
              <span>Hiển thị cả Rack đã thu hồi / rỗng</span>
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
          dataSource={filteredRacks}
          scroll={{ x: 1150 }}
          pagination={{
            pageSize: 15,
            showSizeChanger: true,
            showTotal: (total) => `Tổng ${total} Rack`,
          }}
          locale={{
            emptyText: (
              <div className="py-8 text-center text-slate-400">
                <InboxOutlined className="text-3xl mb-2 block mx-auto" />
                <span>Không có Container / Rack nào đang hoạt động</span>
              </div>
            ),
          }}
        />
      </Card>

      {/* Modal 1: Đồng bộ bypass (vị trí + stage + note) */}
      <Modal
        title={
          <div className="flex items-center gap-2">
            <EnvironmentOutlined className="text-brand-primary" />
            <span>
              Đồng bộ bypass Rack:{' '}
              <strong className="font-mono text-brand-primary">
                {editingRack?.container_code}
              </strong>
            </span>
          </div>
        }
        open={Boolean(editingRack)}
        onCancel={() => {
          setEditingRack(null);
          setUpdateErrorMsg(null);
          locationForm.resetFields();
        }}
        onOk={handleConfirmUpdateLocation}
        confirmLoading={syncBypassMutation.isPending}
        okText="Xác nhận bypass"
        cancelText="Hủy"
        destroyOnClose
        width={640}
      >
        {editingRack && (
          <div className="space-y-4 pt-2">
            <Alert
              type="info"
              showIcon
              message="Bypass /complete-stage (admin)"
              description={
                bypassMode === 'DISPATCH_TO_WASH'
                  ? 'Xe còn tại CNC cuối: stage = bước is_final_cnc_step; tạo MOVE_TO_WASH/AMR. Chỉ chọn ô rửa (optional).'
                  : 'Chọn một node thuộc route model: hệ thống suy stage (CNC→S, Wash→final, NL→0), đồng bộ Fleet + production_record. Node ngoài route bị khóa.'
              }
            />

            {updateErrorMsg && (
              <Alert
                type="error"
                showIcon
                message="Không thể đồng bộ bypass"
                description={updateErrorMsg}
              />
            )}

            <div className="rounded-lg bg-slate-50 p-3 text-xs space-y-1 border border-slate-200">
              <div>
                <span className="text-slate-500">Mã Rack:</span>{' '}
                <strong className="font-mono text-slate-900">
                  {editingRack.container_code}
                </strong>
              </div>
              <div>
                <span className="text-slate-500">Vị trí hiện tại:</span>{' '}
                <strong className="text-slate-800">
                  {editingRack.location_name ||
                    editingRack.location_code ||
                    'Chưa có vị trí (Bãi trống)'}
                </strong>
              </div>
              {editingRack.item_name && (
                <div>
                  <span className="text-slate-500">Model đang chứa:</span>{' '}
                  <strong className="text-slate-800">
                    {editingRack.item_name} ({editingRack.item_sku}) — Lv{' '}
                    {editingRack.current_stage_level}
                  </strong>
                </div>
              )}
            </div>

            <Form form={locationForm} layout="vertical">
              <Form.Item
                name="mode"
                label="Chế độ bypass"
                rules={[{ required: true, message: 'Chọn chế độ bypass' }]}
              >
                <Radio.Group className="flex flex-col gap-2">
                  <Radio value="SYNC_PHYSICAL">
                    SYNC_PHYSICAL — xe đã ở đúng chỗ (kể cả ô rửa / CNC tiếp)
                  </Radio>
                  <Radio value="DISPATCH_TO_WASH">
                    DISPATCH_TO_WASH — còn ở CNC cuối, điều AMR sang rửa
                  </Radio>
                </Radio.Group>
              </Form.Item>

              {!editingRack.item_id && (
                <Alert
                  type="warning"
                  showIcon
                  message="Rack chưa gắn Model — không suy được stage từ route."
                />
              )}
              {editingRack.item_id && !bypassRouteCtx && (
                <Alert
                  type="warning"
                  showIcon
                  message="Model chưa có quy trình active — chỉ có thể chọn được sau khi cấu hình route."
                />
              )}
              {bypassRouteCtx && (
                <div className="text-xs text-slate-500 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                  Route <strong className="font-mono">{bypassRouteCtx.routeCode}</strong>
                  {' · '}
                  CNC cuối (is_final_cnc_step) ={' '}
                  <strong>Lv {bypassRouteCtx.finalStage}</strong>
                  {derivedBypassStage != null && (
                    <>
                      {' · '}
                      Stage sẽ ghi:{' '}
                      <strong className="text-brand-primary">Lv {derivedBypassStage}</strong>
                    </>
                  )}
                </div>
              )}

              <Form.Item
                name="location_id"
                label={
                  bypassMode === 'DISPATCH_TO_WASH'
                    ? 'Ô rửa ưu tiên (không bắt buộc)'
                    : 'Vị trí/node thực tế (suy stage theo route)'
                }
                rules={
                  bypassMode === 'SYNC_PHYSICAL'
                    ? [{ required: true, message: 'Chọn vị trí/node thuộc quy trình model' }]
                    : []
                }
                getValueProps={(value) => ({
                  value: value != null ? String(value) : undefined,
                })}
                normalize={(value) =>
                  value == null || value === '' ? undefined : Number(value)
                }
              >
                <NodeSelectWithMap
                  allowClear={bypassMode === 'DISPATCH_TO_WASH'}
                  placeholder={
                    bypassMode === 'DISPATCH_TO_WASH'
                      ? 'Để trống = hệ thống tự chọn ô rửa trống'
                      : 'Chọn node trong route hoặc mở Bản đồ...'
                  }
                  options={bypassLocationSelectOptions}
                  onOpenMap={openBypassMapPicker}
                />
              </Form.Item>

              <Form.Item
                name="note"
                label="Ghi chú bypass (bắt buộc → production_record)"
                rules={[
                  { required: true, message: 'Nhập lý do bypass' },
                  { whitespace: true, message: 'Ghi chú không được để trống' },
                  { max: 1000, message: 'Tối đa 1000 ký tự' },
                ]}
              >
                <TextArea
                  rows={3}
                  placeholder="VD: Op quên bấm hoàn thành, đã đẩy tay từ CNC01 sang CNC02"
                  maxLength={1000}
                  showCount
                />
              </Form.Item>
            </Form>
          </div>
        )}
      </Modal>

      {/* Modal 2: Xóa / Thu hồi Rack (giống API xóa ở bãi xe trống containerOut) */}
      <Modal
        title={
          <div className="flex items-center gap-2 text-red-600">
            <ExclamationCircleOutlined />
            <span>
              Xác nhận xóa / thu hồi Rack:{' '}
              <strong className="font-mono">{deletingRack?.container_code}</strong>
            </span>
          </div>
        }
        open={Boolean(deletingRack)}
        onCancel={() => {
          setDeletingRack(null);
          setDeleteErrorMsg(null);
        }}
        onOk={() => {
          if (!deletingRack) return;
          setDeleteErrorMsg(null);
          removeMutation.mutate(deletingRack.id);
        }}
        confirmLoading={removeMutation.isPending}
        okText="Xác nhận xóa Rack"
        okButtonProps={{ danger: true }}
        cancelText="Hủy"
        destroyOnClose
      >
        {deletingRack && (
          <div className="space-y-4 pt-2">
            <Alert
              type="warning"
              showIcon
              message="Đồng bộ xóa với KUKA Fleet (containerQuery → containerOut)"
              description={
                <span>
                  Hệ thống sẽ truy vấn{' '}
                  <code className="font-mono font-semibold">/amr/containerQuery</code> theo mã
                  Rack. Nếu Fleet không còn container → thu hồi ngay trên WMS. Nếu còn và không
                  đang được AMR mang → gọi{' '}
                  <code className="font-mono font-semibold">/amr/containerOut</code> rồi mới giải
                  phóng vị trí{' '}
                  <strong>
                    {deletingRack.location_name ||
                      deletingRack.location_code ||
                      'hiện tại'}
                  </strong>
                  . Query/Out lỗi hoặc xe đang trên AMR → WMS giữ nguyên.
                </span>
              }
            />

            {deleteErrorMsg && (
              <Alert
                type="error"
                showIcon
                message="Không thể xóa Rack — KUKA Fleet báo lỗi"
                description={deleteErrorMsg}
              />
            )}

            <div className="rounded-lg bg-slate-50 p-3 text-xs space-y-1.5 border border-slate-200">
              <div>
                <span className="text-slate-500">Mã Rack:</span>{' '}
                <strong className="font-mono text-slate-900">
                  {deletingRack.container_code}
                </strong>
              </div>
              <div>
                <span className="text-slate-500">Vị trí đang đỗ:</span>{' '}
                <strong className="text-slate-800">
                  {deletingRack.location_name ||
                    deletingRack.location_code ||
                    'Không có'}
                </strong>
                {deletingRack.location_label && (
                  <span className="text-slate-500 font-mono">
                    {' '}
                    ({deletingRack.location_label})
                  </span>
                )}
              </div>
              {deletingRack.item_name && (
                <div>
                  <span className="text-slate-500">Model &amp; Công đoạn:</span>{' '}
                  <strong className="text-slate-800">
                    {deletingRack.item_name} ({deletingRack.item_sku}) — Lv{' '}
                    {deletingRack.current_stage_level}
                  </strong>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>

      <MapNodePickerModal
        open={mapPicker.open}
        onClose={closeMapPicker}
        title={mapPicker.title}
        isOverview={mapPicker.isOverview}
        currentSelectedNodeLabel={mapPicker.currentSelectedNodeLabel}
        availableNodes={availableNodes}
        assignedNodesMap={assignedNodesMap}
        currentLocationId={mapPicker.currentLocationId}
        selectedInForm={mapPicker.selectedInForm}
        onSelectNode={mapPicker.onSelect}
      />
    </div>
  );
}
