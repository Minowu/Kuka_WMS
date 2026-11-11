import { Select, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { Table } from '@/components/ui';
import { AUDIT_EVENT_LABELS, FAILURE_REASON_LABELS, LOG_PAGE_SIZE } from '@/constants/auditLog';
import { useAuditLogs } from '@/hooks/useAuditLogs';
import { useLogFilters } from '@/hooks/useLogFilters';
import type { AuditLog, AuditLogParams } from '@/types/auditLog';
import LogFilterBar from './LogFilterBar';
import { deviceColumn, resultColumn, timeColumn, userColumn } from './logCommonColumns';

const EVENT_OPTIONS = Object.entries(AUDIT_EVENT_LABELS).map(([value, label]) => ({ value, label }));

const columns: ColumnsType<AuditLog> = [
  timeColumn<AuditLog>(),
  {
    title: 'Sự kiện',
    dataIndex: 'event_type',
    key: 'event_type',
    width: 160,
    render: (value: AuditLog['event_type']) => AUDIT_EVENT_LABELS[value] ?? value,
  },
  userColumn<AuditLog>(),
  resultColumn<AuditLog>(),
  {
    title: 'Lý do',
    dataIndex: 'failure_reason',
    key: 'failure_reason',
    width: 170,
    render: (value: string | null) => (value ? FAILURE_REASON_LABELS[value] ?? value : '—'),
  },
  deviceColumn<AuditLog>(),
  {
    title: 'API',
    dataIndex: 'path',
    key: 'path',
    align: 'left',
    render: (value: string | null) => <span className="font-mono text-xs">{value ?? '—'}</span>,
  },
  {
    title: 'Trình duyệt',
    dataIndex: 'user_agent',
    key: 'user_agent',
    width: 120,
    render: (value: string | null) =>
      value ? (
        <Tooltip title={value}>
          <span className="text-xs text-slate-500 underline decoration-dotted cursor-help">Xem</span>
        </Tooltip>
      ) : (
        '—'
      ),
  },
];

export default function AuditLogTab() {
  const { filters, params, page, setPage, setFilter, resetFilters } = useLogFilters<AuditLogParams>();
  const { data, isFetching } = useAuditLogs(params);

  return (
    <div className="space-y-4">
      <LogFilterBar filters={filters} onFilterChange={setFilter} onReset={resetFilters}>
        <Select
          size="large"
          allowClear
          placeholder="Loại sự kiện"
          className="!w-48"
          value={filters.event_type}
          options={EVENT_OPTIONS}
          onChange={(value?: string) => setFilter('event_type', value)}
        />
      </LogFilterBar>
      <Table<AuditLog>
        rowKey="id"
        columns={columns}
        dataSource={data?.items ?? []}
        loading={isFetching}
        scroll={{ x: 1200 }}
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
