import { useEffect, useMemo, useState } from 'react';
import { message } from '@/components/ui';
import { getUserLocationsApi } from '@/api/machine';
import { useStationCatalog } from '@/hooks/useStations';
import { useUpdateUserLocations } from '@/hooks/useMachines';
import type { User } from '@/types/auth';
import { getApiErrorMessage } from '@/utils/apiErrorMessage';
import {
  AREA_NAMES,
  detectUserArea,
  getAreaLocationIds,
  getRoleArea,
  type ProductionArea,
} from './stationAssignmentConfig';

interface UseStationAssignmentParams {
  open: boolean;
  user: User | null;
  onClose: () => void;
}

/** Quy tắc: 1 tài khoản chỉ trực tại 1 khu vực, trong khu đó được chọn nhiều vị trí. */
export function useStationAssignment({ open, user, onClose }: UseStationAssignmentParams) {
  const { data: catalog, isLoading: isCatalogLoading } = useStationCatalog();
  const updateMutation = useUpdateUserLocations();

  const [selectedArea, setSelectedArea] = useState<ProductionArea>('cnc');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [isLoadingUserLocs, setIsLoadingUserLocs] = useState(false);

  useEffect(() => {
    if (open && user && catalog) {
      setIsLoadingUserLocs(true);
      getUserLocationsApi(user.id)
        .then((ids) => {
          const userIds = ids || [];
          setSelectedIds(userIds);
          setSelectedArea(detectUserArea(user, catalog, userIds));
        })
        .catch(() => {
          message.error('Không thể tải danh sách vị trí phân quyền của tài khoản');
        })
        .finally(() => setIsLoadingUserLocs(false));
    } else if (!open) {
      setSelectedIds([]);
      setSelectedArea('cnc');
    }
  }, [open, user, catalog]);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  // Đổi khu vực → bỏ hết vị trí của khu cũ để giữ đúng quy tắc 1 tài khoản = 1 khu
  const changeArea = (area: ProductionArea) => {
    if (area === selectedArea) return;
    setSelectedArea(area);
    setSelectedIds([]);
  };

  const toggleLocation = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  // Chọn máy CNC = chọn toàn bộ vị trí đỗ của máy đó
  const toggleMachine = (slotIds: number[]) => {
    const allSelected = slotIds.length > 0 && slotIds.every((id) => selectedSet.has(id));
    setSelectedIds((prev) =>
      allSelected ? prev.filter((id) => !slotIds.includes(id)) : Array.from(new Set([...prev, ...slotIds]))
    );
  };

  const selectAll = () => {
    if (catalog) setSelectedIds(getAreaLocationIds(catalog, selectedArea));
  };

  const clearAll = () => setSelectedIds([]);

  const save = async () => {
    if (!user) return;
    try {
      await updateMutation.mutateAsync({ userId: user.id, locationIds: selectedIds });
      message.success(
        `Đã phân quyền ${selectedIds.length} vị trí thuộc [${AREA_NAMES[selectedArea]}] cho '${user.username}'!`
      );
      onClose();
    } catch (err) {
      message.error(getApiErrorMessage(err, 'Không thể lưu phân quyền trạm'));
    }
  };

  return {
    catalog,
    isLoading: isCatalogLoading || isLoadingUserLocs,
    isSaving: updateMutation.isPending,
    roleArea: getRoleArea(user),
    selectedArea,
    selectedIds,
    selectedSet,
    changeArea,
    toggleLocation,
    toggleMachine,
    selectAll,
    clearAll,
    save,
  };
}
