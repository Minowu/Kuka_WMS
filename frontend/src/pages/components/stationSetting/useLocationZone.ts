import { useState } from 'react';
import { Form, message } from '@/components/ui';
import {
  useCreateStationLocation,
  useDeleteStationLocation,
  useUpdateStationLocation,
} from '@/hooks/useStations';
import type { StationCatalogItem } from '@/types/station';
import { padTwoDigits } from '@/utils/number';
import type { LocationZoneConfig } from './locationZoneConfig';
import type { NodeTools } from './stationSettingTypes';
import { showStationError } from './showStationError';

interface LocationFormValues {
  node_label: string;
  location_name: string;
}

/** Thêm / sửa / xóa một vị trí đơn (ô cấp phôi, slot tẩy rửa, bãi đệm). */
export function useLocationZone(
  config: LocationZoneConfig,
  items: StationCatalogItem[],
  nodeTools: NodeTools
) {
  const [form] = Form.useForm<LocationFormValues>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<StationCatalogItem | null>(null);

  const createMutation = useCreateStationLocation();
  const updateMutation = useUpdateStationLocation();
  const deleteMutation = useDeleteStationLocation();

  const openCreate = () => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({ location_name: `${config.namePrefix}-${padTwoDigits(items.length + 1)}` });
    setIsModalOpen(true);
  };

  const openEdit = (item: StationCatalogItem) => {
    setEditingItem(item);
    form.resetFields();
    form.setFieldsValue({
      location_name: item.location_name || '',
      node_label: nodeTools.matchNodeLabel(item.node_label, item.location_code),
    });
    setIsModalOpen(true);
  };

  const closeModal = () => setIsModalOpen(false);

  const submit = async () => {
    try {
      const values = await form.validateFields();
      const name = values.location_name.trim();
      const selectedNode = nodeTools.availableNodes.find((n) => n.node_label === values.node_label);

      if (editingItem) {
        await updateMutation.mutateAsync({
          id: editingItem.id,
          data: {
            location_name: name,
            node_label: values.node_label,
            map_x: selectedNode ? selectedNode.map_x : editingItem.map_x ?? undefined,
            map_y: selectedNode ? selectedNode.map_y : editingItem.map_y ?? undefined,
          },
        });
        message.success(`Cập nhật ${config.entityLabel} '${name}' thành công!`);
      } else {
        await createMutation.mutateAsync({
          location_code: selectedNode?.node_label || values.node_label,
          location_name: name,
          location_type: config.locationType,
          node_label: values.node_label,
          map_x: selectedNode?.map_x,
          map_y: selectedNode?.map_y,
          position_index: items.length + 1,
        });
        message.success(`Gán ${config.entityLabel} '${name}' (Node ${values.node_label}) thành công!`);
      }
      setIsModalOpen(false);
    } catch (err) {
      showStationError(err, `Không thể lưu ${config.entityLabel}`);
    }
  };

  const remove = async (item: StationCatalogItem) => {
    try {
      await deleteMutation.mutateAsync(item.id);
      message.success(`Đã xóa ${config.entityLabel} '${item.location_code}'`);
    } catch (err) {
      showStationError(err, `Không thể xóa ${config.entityLabel}`);
    }
  };

  return {
    form,
    isModalOpen,
    editingItem,
    isSaving: createMutation.isPending || updateMutation.isPending,
    openCreate,
    openEdit,
    closeModal,
    submit,
    remove,
  };
}

export type LocationZoneState = ReturnType<typeof useLocationZone>;
