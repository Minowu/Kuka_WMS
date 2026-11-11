import { Input, Select, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Table } from '@/components/ui';
import { ACTION_METHODS, LOG_PAGE_SIZE } from '@/constants/auditLog';
import { useActionLogs } from '@/hooks/useAuditLogs';
import { useLogFilters } from '@/hooks/useLogFilters';
import type { ActionLog, ActionLogParams } from '@/types/auditLog';
import ActionLogDetail from './ActionLogDetail';
import LogFilterBar from './LogFilterBar';
import { deviceColumn, resultColumn, timeColumn, userColumn } from './logCommonColumns';

const METHOD_COLORS: Record<string, string> = {
  POST: 'blue',
  PUT: 'orange',
  PATCH: 'gold',
  DELETE: 'red',
};

const METHOD_OPTIONS = ACTION_METHODS.map((m) => ({ value: m, label: m }));

const columns: ColumnsType<ActionLog> = [
  timeColumn<ActionLog>(),
  userColumn<ActionLog>(),
  {
    title: 'Thao tác',
    dataIndex: 'action',
    key: 'action',
    width: 200,
    render: (value: string | null) => <span className="font-medium">{value ?? '—'}</span>,
  },
  {
    title: 'API',
    key: 'api',
    align: 'left',
    render: (_value, record) => (
      <span className="font-mono text-xs">
        <Tag color={METHOD_COLORS[record.method]} className="!mr-2">
          {record.method}
        </Tag>
        {record.path}
      </span>
    ),
  },
  {
    title: 'Đối tượng',
    key: 'resource',
    width: 140,
    render: (_value, record) =>
      record.resource_type ? `${record.resource_type}${record.resource_id ? ` #${record.resource_id}` : ''}` : '—',
  },
  resultColumn<ActionLog>(),
  {
    title: 'HTTP',
    dataIndex: 'status_code',
    key: 'status_code',
    width: 80,
  },
  deviceColumn<ActionLog>(),
];

export default function ActionLogTab() {
  const { filters, params, page, setPage, setFilter, resetFilters } = useLogFilters<ActionLogParams>();
  const { data, isFetching } = useActionLogs(params);

  return (
    <div className="space-y-4">
      <LogFilterBar filters={filters} onFilterChange={setFilter} onReset={resetFilters}>
        <Select
          size="large"
          allowClear
          placeholder="Method"
          className="!w-32"
          value={filters.method}
          options={METHOD_OPTIONS}
          onChange={(value?: string) => setFilter('method', value)}
        />
        <Input.Search
          key={`action-${filters.action ?? ''}`}
          defaultValue={filters.action}
          size="large"
          allowClear
          placeholder="Tên thao tác"
          className="!w-52"
          onSearch={(value) => setFilter('action', value.trim())}
        />
      </LogFilterBar>
      <Table<ActionLog>
        rowKey="id"
        columns={columns}
        dataSource={data?.items ?? []}
        loading={isFetching}
        scroll={{ x: 1300 }}
        expandable={{ expandedRowRender: (record) => <ActionLogDetail record={record} /> }}
        pagination={{
          current: page,
          pageSize: LOG_PAGE_SIZE,
          total: data?.total ?? 0,
          showSizeChanger: false,
          showTotal: (total) => `${total} bản ghi`,
          onChange: setPage,
        }}
      />
    </div>
  );
}
