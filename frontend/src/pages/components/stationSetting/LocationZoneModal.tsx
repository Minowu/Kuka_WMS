import { Form, Input, Modal } from '@/components/ui';
import type { LocationZoneConfig } from './locationZoneConfig';
import type { NodeTools } from './stationSettingTypes';
import type { LocationZoneState } from './useLocationZone';
import NodeSelectWithMap from './NodeSelectWithMap';

interface LocationZoneModalProps {
  config: LocationZoneConfig;
  zone: LocationZoneState;
  nodeTools: NodeTools;
}

export default function LocationZoneModal({ config, zone, nodeTools }: LocationZoneModalProps) {
  const { form, editingItem } = zone;

  const openMap = () => {
    nodeTools.openMapPicker({
      title: `Chọn điểm đỗ trên bản đồ cho ${config.entityTitle} ${form.getFieldValue('location_name') || ''}`,
      currentSelectedNodeLabel: form.getFieldValue('node_label'),
      currentLocationId: editingItem?.id,
      onSelect: (node) => form.setFieldsValue({ node_label: node.node_label }),
    });
  };

  return (
    <Modal
      title={editingItem ? `Chỉnh sửa ${config.entityLabel} '${editingItem.location_code}'` : config.createModalTitle}
      open={zone.isModalOpen}
      onCancel={zone.closeModal}
      onOk={zone.submit}
      confirmLoading={zone.isSaving}
      okText={editingItem ? 'Lưu thay đổi' : config.createOkText}
      cancelText="Hủy"
      centered
      width={480}
    >
      <Form form={form} layout="vertical" className="mt-4">
        <Form.Item label="Chọn Node Bản Đồ KUKA" required>
          <Form.Item
            name="node_label"
            noStyle
            rules={[{ required: true, message: 'Vui lòng chọn Node Map KUKA!' }]}
          >
            <NodeSelectWithMap
              placeholder="Chọn điểm đỗ Node trên Map (chưa gán)"
              options={nodeTools.getNodeOptions({ currentLocationId: editingItem?.id })}
              onOpenMap={openMap}
            />
          </Form.Item>
        </Form.Item>

        <Form.Item
          name="location_name"
          label="Tên Đặt Nghiệp Vụ (Hiển thị PDA / Web)"
          rules={[{ required: true, message: `Vui lòng nhập tên ${config.entityLabel}!` }]}
        >
          <Input placeholder={config.namePlaceholder} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
