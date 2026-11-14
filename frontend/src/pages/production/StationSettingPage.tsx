import { useState, type ReactNode } from 'react';
import { Tabs } from 'antd';
import {
  CarOutlined,
  EnvironmentOutlined,
  ExperimentOutlined,
  InboxOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { Button, message } from '@/components/ui';
import Hero from '@/components/shared/Hero';
import MapNodePickerModal from '@/pages/components/MapNodePickerModal';
import { useAvailableNodes, useStationCatalog } from '@/hooks/useStations';
import { useStationNodes } from '@/pages/components/stationSetting/useStationNodes';
import { useMapPicker } from '@/pages/components/stationSetting/useMapPicker';
import { LOCATION_ZONES } from '@/pages/components/stationSetting/locationZoneConfig';
import type { NodeTools } from '@/pages/components/stationSetting/stationSettingTypes';
import LocationZoneTab from '@/pages/components/stationSetting/LocationZoneTab';
import CncMachineTab from '@/pages/components/stationSetting/CncMachineTab';

const renderTabLabel = (icon: ReactNode, text: string) => (
  <span className="flex items-center gap-2">
    {icon}
    <span>{text}</span>
  </span>
);

export default function StationSettingPage() {
  const { data: catalog, isLoading } = useStationCatalog();
  const { data: availableNodes = [] } = useAvailableNodes();
  const { assignedNodesMap, matchNodeLabel, getNodeOptions } = useStationNodes(catalog, availableNodes);
  const { mapPicker, openMapPicker, closeMapPicker } = useMapPicker();
  const [activeTab, setActiveTab] = useState('raw_material');

  const nodeTools: NodeTools = { availableNodes, getNodeOptions, matchNodeLabel, openMapPicker };
  const rawMaterials = catalog?.raw_materials || [];
  const machines = catalog?.machines || [];
  const washingSlots = catalog?.washing_slots || [];
  const emptyBuffers = catalog?.empty_buffers || [];

  const openOverviewMap = () => {
    openMapPicker({
      title: 'Sơ đồ Bản đồ Xưởng KUKA (Trực quan hóa vị trí & Node)',
      isOverview: true,
      onSelect: (node) => {
        message.info(`Bạn đang chọn Node ${node.node_number} (Tọa độ: ${node.map_x}, ${node.map_y})`);
      },
    });
  };

  const tabItems = [
    {
      key: 'raw_material',
      label: renderTabLabel(
        <InboxOutlined className="text-amber-600 text-base" />,
        `Khu Cấp Phôi (${rawMaterials.length})`
      ),
      children: (
        <LocationZoneTab
          config={LOCATION_ZONES.raw_material}
          items={rawMaterials}
          isLoading={isLoading}
          nodeTools={nodeTools}
        />
      ),
    },
    {
      key: 'cnc',
      label: renderTabLabel(
        <ToolOutlined className="text-brand-primary text-base" />,
        `Khu Máy CNC (${machines.length})`
      ),
      children: <CncMachineTab machines={machines} nodeTools={nodeTools} />,
    },
    {
      key: 'washing',
      label: renderTabLabel(
        <ExperimentOutlined className="text-emerald-600 text-base" />,
        `Khu Tẩy Rửa (${washingSlots.length})`
      ),
      children: (
        <LocationZoneTab
          config={LOCATION_ZONES.washing}
          items={washingSlots}
          isLoading={isLoading}
          nodeTools={nodeTools}
        />
      ),
    },
    {
      key: 'empty_buffer',
      label: renderTabLabel(
        <CarOutlined className="text-blue-600 text-base" />,
        `Bãi Đệm Xe Rỗng (${emptyBuffers.length})`
      ),
      children: (
        <LocationZoneTab
          config={LOCATION_ZONES.empty_buffer}
          items={emptyBuffers}
          isLoading={isLoading}
          nodeTools={nodeTools}
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <Hero
        title="Cấu Hình Trạm & Phân Khu Xưởng"
        extra={
          <Button
            icon={<EnvironmentOutlined />}
            onClick={openOverviewMap}
            className="!bg-brand-primary hover:!bg-stripe-primary-deep !border-none !text-white !h-10 !px-4 !rounded-lg font-semibold shadow-sm flex items-center gap-1.5"
          >
            🗺️ Mở Bản Đồ Xưởng
          </Button>
        }
      />

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        type="card"
        className="[&_.ant-tabs-nav]:!mb-4 [&_.ant-tabs-tab]:!font-semibold [&_.ant-tabs-tab-active]:!text-brand-primary"
        items={tabItems}
      />

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
