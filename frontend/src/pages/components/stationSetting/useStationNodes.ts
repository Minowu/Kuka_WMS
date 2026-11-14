import { useCallback, useMemo } from 'react';
import type {
  AvailableMapNode,
  StationCatalogItem,
  StationCatalogResponse,
} from '@/types/station';
import type { AssignedNodeInfo, NodeOption, NodeOptionFilter } from './stationSettingTypes';

const toKey = (value?: string | number | null) => String(value ?? '').toLowerCase();

/** Gom toàn bộ node đã gán ở mọi khu vực, tra cứu theo location_code / location_label / node_label. */
function buildAssignedNodesMap(catalog?: StationCatalogResponse) {
  const map = new Map<string, AssignedNodeInfo>();

  const register = (item: StationCatalogItem, info: AssignedNodeInfo) => {
    [item.location_code, item.location_label, item.node_label].forEach((key) => {
      if (key) map.set(toKey(key), info);
    });
  };

  const registerZone = (items: StationCatalogItem[] | undefined, zone: string) => {
    items?.forEach((item) =>
      register(item, { id: item.id, name: item.location_name || item.location_code, zone })
    );
  };

  registerZone(catalog?.raw_materials, 'Khu Cấp Phôi');
  catalog?.machines?.forEach((m) => {
    m.slots?.forEach((s) =>
      register(s, { id: s.id, name: `${m.machine_code} (POS${s.position_index})`, zone: 'Khu Máy CNC' })
    );
  });
  registerZone(catalog?.washing_slots, 'Khu Tẩy Rửa');
  registerZone(catalog?.empty_buffers, 'Bãi Đệm Xe Rỗng');

  return map;
}

export function useStationNodes(
  catalog: StationCatalogResponse | undefined,
  availableNodes: AvailableMapNode[]
) {
  const assignedNodesMap = useMemo(() => buildAssignedNodesMap(catalog), [catalog]);

  // node_label trong DB có thể là "20" hoặc "CNC001-CNC001-20" → quy về node_label chuẩn của bản đồ
  const matchNodeLabel = useCallback(
    (val?: string | null, locCode?: string | null): string | undefined => {
      if (!val && !locCode) return undefined;
      const keys = [toKey(val), toKey(locCode)];
      const found = availableNodes.find(
        (n) => keys.includes(toKey(n.node_label)) || keys.includes(toKey(n.node_number))
      );
      return found ? found.node_label : val || locCode || undefined;
    },
    [availableNodes]
  );

  // Node đã gán ở khu khác hoặc đang được chọn ở slot khác trong form → vô hiệu hóa (xám)
  const getNodeOptions = useCallback(
    (filter: NodeOptionFilter = {}): NodeOption[] => {
      const { currentLocationId, selectedInForm = [], currentSlotNode } = filter;

      return availableNodes.map((n) => {
        const label = toKey(n.node_label);
        const number = toKey(n.node_number);
        const assignedInfo = assignedNodesMap.get(label) || assignedNodesMap.get(number);
        const isCurrentSlotNode = label === toKey(currentSlotNode) || number === toKey(currentSlotNode);
        const isPickedInForm =
          !isCurrentSlotNode &&
          selectedInForm.some((sel) => sel && (toKey(sel) === label || toKey(sel) === number));

        let disabled = false;
        let badge = '[Trống]';

        if (isPickedInForm) {
          disabled = true;
          badge = '[Đang chọn ở vị trí khác trong máy]';
        } else if (assignedInfo) {
          const isAssignedToSelf = !!currentLocationId && assignedInfo.id === currentLocationId;
          disabled = !isAssignedToSelf;
          badge = isAssignedToSelf
            ? `[Hiện tại: ${assignedInfo.name}]`
            : `[Đã gán: ${assignedInfo.name} - ${assignedInfo.zone}]`;
        } else if (n.is_assigned) {
          disabled = true;
          badge = `[Đã gán: ${n.assigned_to || 'Khu khác'}]`;
        }

        return { value: n.node_label, disabled, label: `Node ${n.node_number} ${badge}`, node: n };
      });
    },
    [availableNodes, assignedNodesMap]
  );

  return { assignedNodesMap, matchNodeLabel, getNodeOptions };
}
