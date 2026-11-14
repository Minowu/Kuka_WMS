import { Card, Table } from '@/components/ui';
import type { StationCatalogItem } from '@/types/station';
import type { LocationZoneConfig } from './locationZoneConfig';
import type { NodeTools } from './stationSettingTypes';
import { useLocationZone } from './useLocationZone';
import { buildLocationColumns } from './locationZoneColumns';
import ZoneInfoBanner from './ZoneInfoBanner';
import LocationZoneModal from './LocationZoneModal';

interface LocationZoneTabProps {
  config: LocationZoneConfig;
  items: StationCatalogItem[];
  isLoading: boolean;
  nodeTools: NodeTools;
}

export default function LocationZoneTab({ config, items, isLoading, nodeTools }: LocationZoneTabProps) {
  const zone = useLocationZone(config, items, nodeTools);
  const columns = buildLocationColumns(config, { onEdit: zone.openEdit, onDelete: zone.remove });

  return (
    <div className="space-y-4">
      <ZoneInfoBanner
        theme={config.theme}
        title={config.infoTitle}
        buttonText={config.addButtonText}
        onAdd={zone.openCreate}
      >
        {config.infoText}
      </ZoneInfoBanner>

      <Card className="rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
        <Table<StationCatalogItem>
          loading={isLoading}
          dataSource={items}
          rowKey="id"
          pagination={false}
          className="[&_.ant-table-thead_th]:!bg-slate-50 [&_.ant-table-thead_th]:!text-slate-600 [&_.ant-table-thead_th]:!font-semibold"
          columns={columns}
        />
      </Card>

      <LocationZoneModal config={config} zone={zone} nodeTools={nodeTools} />
    </div>
  );
}
