import { Popconfirm, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, EditOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { Button, Space } from '@/components/ui';
import type { StationCatalogItem } from '@/types/station';
import { compareNatural } from '@/utils/sortByName';
import type { LocationZoneConfig } from './locationZoneConfig';

interface ColumnHandlers {
  onEdit: (item: StationCatalogItem) => void;
  onDelete: (item: StationCatalogItem) => void;
}

const sortByLocationName = (a: StationCatalogItem, b: StationCatalogItem) =>
  compareNatural(a.location_name, b.location_name);

function buildLeadingColumns(config: LocationZoneConfig): ColumnsType<StationCatalogItem> {
  const badgeClass = `font-mono font-bold px-2.5 py-1 rounded-md border ${config.theme.badgeClass}`;

  if (config.tableLayout === 'name_first') {
    return [
      {
        title: 'Tên Đặt Nghiệp Vụ',
        dataIndex: 'location_name',
        key: 'location_name',
        width: 180,
        sorter: sortByLocationName,
        defaultSortOrder: 'ascend',
        render: (text: string | null) => <span className={badgeClass}>{text || '—'}</span>,
      },
      {
        title: 'Mã Node KUKA (UUID Fleet)',
        dataIndex: 'location_code',
        key: 'location_code',
        width: 140,
        render: (text: string) => (
          <span className="font-mono text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded">{text}</span>
        ),
      },
      {
        title: 'Node Bản Đồ',
        key: 'location_label',
        width: 140,
        render: (_, record) => (
          <Tag color="cyan" className="!font-bold !m-0 font-mono">
            Node {record.location_label || record.node_label || '--'}
          </Tag>
        ),
      },
    ];
  }

  return [
    {
      title: config.nameColumnTitle,
      dataIndex: 'location_name',
      key: 'location_name',
      sorter: sortByLocationName,
      defaultSortOrder: 'ascend',
      width: 180,
      render: (text: string | null) => <span className="font-medium text-slate-800">{text || '—'}</span>,
    },
    {
      title: config.codeColumnTitle,
      dataIndex: 'location_code',
      key: 'location_code',
      width: 140,
      render: (text: string) => <span className={badgeClass}>{text}</span>,
    },
    {
      title: 'Node Bản Đồ',
      key: 'node_label',
      width: 180,
      render: (_, record) => (
        <Tag color="cyan" className="font-mono !font-bold">
          Node {record.node_label || '--'}
        </Tag>
      ),
    },
  ];
}

export function buildLocationColumns(
  config: LocationZoneConfig,
  { onEdit, onDelete }: ColumnHandlers
): ColumnsType<StationCatalogItem> {
  return [
    ...buildLeadingColumns(config),
    {
      title: 'Tọa Độ Thực Tế (Map X, Y)',
      key: 'coords',
      width: 220,
      render: (_, record) => (
        <div className="text-xs font-mono text-slate-600 flex items-center justify-center gap-1">
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
      title: 'Thao Tác',
      key: 'actions',
      width: 140,
      align: 'center',
      render: (_, record) => (
        <Space size="small">
          <Button
            variant="outline"
            icon={<EditOutlined />}
            onClick={() => onEdit(record)}
            className={`!h-8 !px-2 text-slate-600 ${config.theme.editHoverClass}`}
            title="Sửa"
          />
          <Popconfirm
            title={`Xóa ${config.entityLabel} này?`}
            description="Bạn có chắc chắn muốn xóa vị trí này không?"
            okText="Xóa"
            cancelText="Hủy"
            okButtonProps={{ danger: true }}
            onConfirm={() => onDelete(record)}
          >
            <Button
              variant="outline"
              icon={<DeleteOutlined className="text-red-500" />}
              className="!h-8 !px-2 hover:border-red-400"
              title="Xóa"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];
}
