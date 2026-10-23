import { useEffect, useState, useMemo } from 'react';
import {
  Modal,
  Button,
  message,
  Space,
  cn,
} from '@/components/ui';
import { Checkbox, Tag, Spin, Segmented, Alert } from 'antd';
import {
  ToolOutlined,
  CheckOutlined,
  EnvironmentOutlined,
  InboxOutlined,
  ClearOutlined,
  ClusterOutlined,
  ExperimentOutlined,
  CheckSquareOutlined,
} from '@ant-design/icons';
import type { User } from '@/types/auth';
import { useStationCatalog } from '@/hooks/useStations';
import { useUpdateUserLocations } from '@/hooks/useMachines';
import { getUserLocationsApi } from '@/api/machine';
import type { StationCatalogItem, MachineCatalogGroup } from '@/types/station';

interface StationAssignmentModalProps {
  open: boolean;
  onClose: () => void;
  user: User | null;
}

type ProductionArea = 'raw_material' | 'cnc' | 'washing';

export default function StationAssignmentModal({
  open,
  onClose,
  user,
}: StationAssignmentModalProps) {
  const { data: catalog, isLoading: isCatalogLoading } = useStationCatalog();
  const updateMutation = useUpdateUserLocations();

  // Tầng 1: Chọn 1 Khu Vực duy nhất
  const [selectedArea, setSelectedArea] = useState<ProductionArea>('cnc');
  // Tầng 2: Danh sách vị trí đã chọn
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [isLoadingUserLocs, setIsLoadingUserLocs] = useState(false);

  useEffect(() => {
    if (open && user && catalog) {
      setIsLoadingUserLocs(true);
      getUserLocationsApi(user.id)
        .then((ids) => {
          const userIds = ids || [];
          setSelectedIds(userIds);

          // Tự động nhận diện khu vực hiện tại của tài khoản
          const rawIds = new Set((catalog.raw_materials || []).map((r) => r.id));
          const washIds = new Set((catalog.washing_slots || []).map((w) => w.id));
          const cncIds = new Set(
            (catalog.machines || []).flatMap((m) => (m.slots || []).map((s) => s.id))
          );

          // Nhận diện theo Role của User trước tiên nếu có role chuyên biệt
          const roleNames = (user.roles || []).map((r) => r.name.toLowerCase());
          const isRawRole = roleNames.some((r) => r.includes('raw'));
          const isCncRole = roleNames.some((r) => r.includes('cnc'));
          const isWashRole = roleNames.some((r) => r.includes('washing') || r.includes('wash'));

          if (isRawRole) {
            setSelectedArea('raw_material');
          } else if (isWashRole) {
            setSelectedArea('washing');
          } else if (isCncRole) {
            setSelectedArea('cnc');
          } else {
            // Fallback theo các location đã được gán trước đó
            const hasWash = userIds.some((id) => washIds.has(id));
            const hasRaw = userIds.some((id) => rawIds.has(id));
            const hasCnc = userIds.some((id) => cncIds.has(id));

            if (hasRaw && !hasCnc && !hasWash) {
              setSelectedArea('raw_material');
            } else if (hasWash && !hasCnc && !hasRaw) {
              setSelectedArea('washing');
            } else {
              setSelectedArea('cnc');
            }
          }
        })
        .catch(() => {
          message.error('Không thể tải danh sách vị trí phân quyền của tài khoản');
        })
        .finally(() => {
          setIsLoadingUserLocs(false);
        });
    } else if (!open) {
      setSelectedIds([]);
      setSelectedArea('cnc');
    }
  }, [open, user, catalog]);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  // Đổi khu vực ở Tầng 1 -> Xóa quyền khu vực cũ để đảm bảo 1 User = 1 Area nghiêm ngặt
  const handleAreaChange = (val: string | number) => {
    const newArea = val as ProductionArea;
    if (newArea === selectedArea) return;
    setSelectedArea(newArea);
    setSelectedIds([]); // Reset vị trí để chuyển sang khu vực mới
  };

  // Toggle từng vị trí đơn lẻ (dùng cho Khu Cấp Phôi & Tẩy Rửa)
  const toggleLocation = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Toggle toàn bộ các slot của máy CNC (POS1, POS2, POS3)
  const toggleMachine = (machineSlots: StationCatalogItem[]) => {
    const slotIds = machineSlots.map((s) => s.id);
    const allSelected = slotIds.length > 0 && slotIds.every((id) => selectedSet.has(id));

    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !slotIds.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...slotIds])));
    }
  };

  // Bulk actions theo từng khu vực
  const handleSelectAllRaw = () => {
    if (!catalog) return;
    const allRawIds = (catalog.raw_materials || []).map((r) => r.id);
    setSelectedIds(allRawIds);
  };

  const handleDeselectAllRaw = () => {
    setSelectedIds([]);
  };

  const handleSelectAllWash = () => {
    if (!catalog) return;
    const allWashIds = (catalog.washing_slots || []).map((w) => w.id);
    setSelectedIds(allWashIds);
  };

  const handleDeselectAllWash = () => {
    setSelectedIds([]);
  };

  const handleSelectAllCnc = () => {
    if (!catalog) return;
    const allCncSlotIds = (catalog.machines || []).flatMap((m) =>
      (m.slots || []).map((s) => s.id)
    );
    setSelectedIds(allCncSlotIds);
  };

  const handleDeselectAllCnc = () => {
    setSelectedIds([]);
  };

  // Lưu phân quyền
  const handleSave = async () => {
    if (!user) return;
    try {
      await updateMutation.mutateAsync({
        userId: user.id,
        locationIds: selectedIds,
      });

      const areaNames: Record<ProductionArea, string> = {
        raw_material: 'Khu Cấp Phôi',
        cnc: 'Khu Máy CNC',
        washing: 'Khu Tẩy Rửa',
      };

      message.success(
        `Đã phân quyền ${selectedIds.length} vị trí thuộc [${areaNames[selectedArea]}] cho '${user.username}'!`
      );
      onClose();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Không thể lưu phân quyền trạm';
      message.error(errorMsg);
    }
  };

  // Helpers badge vị trí POS1..3
  const renderPosBadge = (pos?: number | null) => {
    if (pos === 1) {
      return (
        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 border border-blue-200">
          P1
        </span>
      );
    }
    if (pos === 2) {
      return (
        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 border border-purple-200">
          P2
        </span>
      );
    }
    if (pos === 3) {
      return (
        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 border border-amber-200">
          P3
        </span>
      );
    }
    return (
      <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
        P{pos || '?'}
      </span>
    );
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-800">
          <ClusterOutlined className="text-brand-primary text-xl" />
          <span>
            Phân Quyền Trạm Sản Xuất —{' '}
            <span className="text-brand-primary font-bold">{user?.username}</span>
          </span>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={
        <div className="flex items-center justify-between w-full pt-2">
          <div className="text-xs text-slate-500 font-medium">
            Khu vực:{' '}
            <span className="font-bold text-slate-700">
              {selectedArea === 'raw_material'
                ? 'Khu Cấp Phôi'
                : selectedArea === 'cnc'
                ? 'Khu Máy CNC'
                : 'Khu Tẩy Rửa'}
            </span>{' '}
            | Đã chọn:{' '}
            <span className="font-bold text-brand-primary text-sm">{selectedIds.length}</span> vị trí
          </div>
          <Space>
            <Button variant="outline" onClick={onClose}>
              Hủy
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              loading={updateMutation.isPending}
              icon={<CheckOutlined />}
            >
              Lưu Phân Quyền
            </Button>
          </Space>
        </div>
      }
      centered
      width={760}
      className="[&_.ant-modal-content]:!rounded-2xl"
    >
      {isCatalogLoading || isLoadingUserLocs ? (
        <div className="flex flex-col h-72 items-center justify-center gap-3">
          <Spin size="large" />
          <span className="text-slate-500 text-sm">Đang tải danh mục trạm xưởng...</span>
        </div>
      ) : !catalog ? (
        <div className="p-4 text-red-500">Không thể tải danh mục trạm xưởng.</div>
      ) : (
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1 py-1">
          {/* Alert thông báo nguyên tắc 1 User = 1 Khu Vực */}
          <Alert
            type="info"
            showIcon
            title="Nguyên tắc 1 Tài khoản = 1 Khu vực duy nhất"
            description="Mỗi nhân viên chỉ trực tại đúng 1 khu vực sản xuất. Khi chuyển khu vực, hệ thống sẽ tự động phân công vị trí theo khu vực mới và giải phóng quyền ở các khu vực khác."
            className="rounded-xl text-xs"
          />

          {/* ========================================================================= */}
          {/* TẦNG 1: CHỌN 1 KHU VỰC DUY NHẤT */}
          {/* ========================================================================= */}
          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">
              Tầng 1: Chọn Phân Khu Sản Xuất Trực Thuộc
            </div>

            {(() => {
              const roleNames = (user?.roles || []).map((r) => r.name.toLowerCase());
              const isRawRole = roleNames.some((r) => r.includes('raw'));
              const isCncRole = roleNames.some((r) => r.includes('cnc'));
              const isWashRole = roleNames.some((r) => r.includes('washing') || r.includes('wash'));
              const isSpecificRole = isRawRole || isCncRole || isWashRole;

              return (
                <Segmented
                  block
                  size="large"
                  value={selectedArea}
                  onChange={handleAreaChange}
                  disabled={isSpecificRole}
                  className="p-1 bg-slate-100 rounded-xl font-bold [&_.ant-segmented-item-selected]:!bg-white [&_.ant-segmented-item-selected]:!text-brand-primary [&_.ant-segmented-item-selected]:!shadow-sm"
                  options={[
                    {
                      label: (
                        <div className="flex items-center justify-center gap-2 py-1.5">
                          <InboxOutlined className="text-amber-600 text-base" />
                          <span className="text-sm">📦 Khu Cấp Phôi</span>
                          <Tag color="orange" className="!ml-1 !mr-0 !px-1.5 !text-[11px] !font-bold">
                            {catalog.raw_materials?.length || 0}
                          </Tag>
                        </div>
                      ),
                      value: 'raw_material',
                      disabled: isSpecificRole && !isRawRole,
                    },
                    {
                      label: (
                        <div className="flex items-center justify-center gap-2 py-1.5">
                          <ToolOutlined className="text-brand-primary text-base" />
                          <span className="text-sm">⚙️ Khu Máy CNC</span>
                          <Tag color="blue" className="!ml-1 !mr-0 !px-1.5 !text-[11px] !font-bold">
                            {catalog.machines?.length || 0} máy
                          </Tag>
                        </div>
                      ),
                      value: 'cnc',
                      disabled: isSpecificRole && !isCncRole,
                    },
                    {
                      label: (
                        <div className="flex items-center justify-center gap-2 py-1.5">
                          <ExperimentOutlined className="text-emerald-600 text-base" />
                          <span className="text-sm">🧼 Khu Tẩy Rửa</span>
                          <Tag color="green" className="!ml-1 !mr-0 !px-1.5 !text-[11px] !font-bold">
                            {catalog.washing_slots?.length || 0}
                          </Tag>
                        </div>
                      ),
                      value: 'washing',
                      disabled: isSpecificRole && !isWashRole,
                    },
                  ]}
                />
              );
            })()}
          </div>

          {/* ========================================================================= */}
          {/* TẦNG 2: CHỌN CHI TIẾT THEO KHU VỰC ĐÃ CHỌN */}
          {/* ========================================================================= */}
          <div className="border border-slate-200/90 rounded-xl p-4 bg-slate-50/40 space-y-3">
            {/* 1. KHU CẤP PHÔI */}
            {selectedArea === 'raw_material' && (
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800 text-sm">
                      Danh sách Ô Cấp Phôi (Nguyên Liệu)
                    </span>
                    <span className="text-xs text-slate-400">
                      (Đã chọn {selectedIds.length}/{(catalog.raw_materials || []).length})
                    </span>
                  </div>

                  <Space size="small">
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<CheckSquareOutlined />}
                      onClick={handleSelectAllRaw}
                      className="!h-7 !text-xs !rounded-lg text-amber-700 hover:text-amber-800"
                    >
                      Chọn tất cả
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<ClearOutlined />}
                      onClick={handleDeselectAllRaw}
                      className="!h-7 !text-xs !rounded-lg hover:text-red-500"
                    >
                      Bỏ chọn tất cả
                    </Button>
                  </Space>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                  {(catalog.raw_materials || []).map((slot) => {
                    const isSelected = selectedSet.has(slot.id);
                    return (
                      <div
                        key={slot.id}
                        onClick={() => toggleLocation(slot.id)}
                        className={cn(
                          'flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer text-xs transition-all select-none',
                          isSelected
                            ? 'border-amber-500 bg-amber-50/80 font-semibold text-amber-950 shadow-2xs'
                            : 'border-slate-200 bg-white hover:border-slate-300 text-slate-600'
                        )}
                      >
                        <Checkbox
                          checked={isSelected}
                          className="pointer-events-none"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="font-mono font-bold text-slate-800">{slot.location_code}</div>
                          <div className="text-[10px] text-slate-400 truncate">
                            {slot.node_label ? `Node ${slot.node_label}` : (slot.location_name || 'Ô nạp')}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 2. KHU TẨY RỬA */}
            {selectedArea === 'washing' && (
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-2.5 mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-800 text-sm">
                      Danh sách Slot Khu Tẩy Rửa
                    </span>
                    <span className="text-xs text-slate-400">
                      (Đã chọn {selectedIds.length}/{(catalog.washing_slots || []).length})
                    </span>
                  </div>

                  <Space size="small">
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<CheckSquareOutlined />}
                      onClick={handleSelectAllWash}
                      className="!h-7 !text-xs !rounded-lg text-emerald-700 hover:text-emerald-800"
                    >
                      Chọn tất cả
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<ClearOutlined />}
                      onClick={handleDeselectAllWash}
                      className="!h-7 !text-xs !rounded-lg hover:text-red-500"
                    >
                      Bỏ chọn tất cả
                    </Button>
                  </Space>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-4 gap-2.5">
                  {(catalog.washing_slots || []).map((slot) => {
                    const isSelected = selectedSet.has(slot.id);
                    return (
                      <div
                        key={slot.id}
                        onClick={() => toggleLocation(slot.id)}
                        className={cn(
                          'flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer text-xs transition-all select-none',
                          isSelected
                            ? 'border-emerald-500 bg-emerald-50/80 font-semibold text-emerald-950 shadow-2xs'
                            : 'border-slate-200 bg-white hover:border-slate-300 text-slate-600'
                        )}
                      >
                        <Checkbox
                          checked={isSelected}
                          className="pointer-events-none"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="font-mono font-bold text-slate-800">{slot.location_code}</div>
                          <div className="text-[10px] text-slate-400 truncate">
                            {slot.node_label ? `Node ${slot.node_label}` : (slot.location_name || 'Slot rửa')}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 3. KHU MÁY CNC (Tích chọn máy tự động gán toàn bộ POS1, POS2, POS3) */}
            {selectedArea === 'cnc' && (
              <div>
                <div className="flex items-center justify-between border-b border-slate-200 pb-2.5 mb-3">
                  <div>
                    <span className="font-bold text-slate-800 text-sm">
                      Danh sách Máy CNC trong xưởng
                    </span>
                    <p className="text-[11px] text-slate-500 m-0">
                      Tích chọn máy nào sẽ tự động gán toàn bộ các vị trí đỗ (POS1, POS2, POS3) của máy đó
                    </p>
                  </div>

                  <Space size="small">
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<CheckSquareOutlined />}
                      onClick={handleSelectAllCnc}
                      className="!h-7 !text-xs !rounded-lg text-brand-primary hover:text-brand-primary"
                    >
                      Chọn tất cả máy
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      icon={<ClearOutlined />}
                      onClick={handleDeselectAllCnc}
                      className="!h-7 !text-xs !rounded-lg hover:text-red-500"
                    >
                      Bỏ chọn tất cả
                    </Button>
                  </Space>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {(catalog.machines || []).map((machine) => {
                    const machineSlots = machine.slots || [];
                    const slotIds = machineSlots.map((s) => s.id);
                    const allSelected =
                      slotIds.length > 0 && slotIds.every((id) => selectedSet.has(id));
                    const partiallySelected =
                      !allSelected && slotIds.some((id) => selectedSet.has(id));

                    return (
                      <div
                        key={machine.id}
                        className={cn(
                          'border rounded-xl transition-all p-3 cursor-pointer select-none',
                          allSelected
                            ? 'border-brand-primary/60 bg-orange-50/20 shadow-xs'
                            : partiallySelected
                            ? 'border-blue-300 bg-blue-50/10'
                            : 'border-slate-200 bg-white hover:border-slate-300'
                        )}
                        onClick={() => toggleMachine(machineSlots)}
                      >
                        {/* Machine Header */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2.5">
                            <Checkbox
                              checked={allSelected}
                              indeterminate={partiallySelected}
                              className="pointer-events-none"
                            />
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="font-bold text-slate-800 text-sm">
                                  {machine.machine_code}
                                </span>
                                <span className="text-xs text-slate-400">
                                  ({machine.machine_name || `Máy ${machine.machine_code}`})
                                </span>
                              </div>
                            </div>
                          </div>

                          <Tag color="blue" className="!text-[11px] !font-bold !m-0">
                            {machineSlots.length} Vị trí
                          </Tag>
                        </div>

                        {/* Machine Slots Preview */}
                        <div className="flex flex-wrap gap-1.5 pl-6">
                          {machineSlots.map((slot, sIdx) => {
                            const isSlotSelected = selectedSet.has(slot.id);
                            const pos = slot.position_index || sIdx + 1;
                            return (
                              <div
                                key={slot.id || sIdx}
                                className={cn(
                                  'flex items-center gap-1 px-2 py-1 rounded-md text-[11px] border font-mono transition-colors',
                                  isSlotSelected
                                    ? 'bg-orange-100/60 border-orange-200 text-orange-950 font-semibold'
                                    : 'bg-slate-50 border-slate-100 text-slate-500'
                                )}
                              >
                                {renderPosBadge(pos)}
                                <span>{slot.location_code}</span>
                                {slot.node_label && (
                                  <span className="text-[10px] text-slate-400">
                                    (Node {slot.node_label})
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
