import type { ReactNode } from 'react';
import { DatePicker, Input, Select } from 'antd';
import dayjs from 'dayjs';
import { Button } from '@/components/ui';
import { LOG_RESULT_LABELS } from '@/constants/auditLog';
import { useDevices } from '@/hooks/useAuditLogs';
import type { CommonLogParams } from '@/types/auditLog';

interface LogFilterBarProps {
  filters: CommonLogParams;
  onFilterChange: (key: keyof CommonLogParams, value: string | undefined) => void;
  onReset: () => void;
  children?: ReactNode;
}

const RESULT_OPTIONS = Object.entries(LOG_RESULT_LABELS).map(([value, label]) => ({ value, label }));

export default function LogFilterBar({ filters, onFilterChange, onReset, children }: LogFilterBarProps) {
  const { data: devices = [] } = useDevices();
  const deviceOptions = devices.map((d) => ({ value: d.name, label: `${d.name} (${d.ip_address})` }));
  const range = filters.date_from && filters.date_to
    ? ([dayjs(filters.date_from), dayjs(filters.date_to)] as [dayjs.Dayjs, dayjs.Dayjs])
    : null;

  return (
    <div className="flex flex-wrap items-center gap-3">
      <DatePicker.RangePicker
        size="large"
        showTime
        format="DD/MM/YYYY HH:mm"
        value={range}
        onChange={(dates) => {
          onFilterChange('date_from', dates?.[0]?.toISOString());
          onFilterChange('date_to', dates?.[1]?.toISOString());
        }}
      />
      {/* key remounts the uncontrolled input so "Xoá lọc" also clears the typed text */}
      <Input.Search
        key={`username-${filters.username ?? ''}`}
        defaultValue={filters.username}
        size="large"
        allowClear
        placeholder="Tên đăng nhập"
        className="!w-52"
        onSearch={(value) => onFilterChange('username', value.trim())}
      />
      <Input.Search
        key={`ip-${filters.ip ?? ''}`}
        defaultValue={filters.ip}
        size="large"
        allowClear
        placeholder="IP"
        className="!w-44"
        onSearch={(value) => onFilterChange('ip', value.trim())}
      />
      <Select
        size="large"
        allowClear
        showSearch
        placeholder="Thiết bị"
        className="!w-56"
        value={filters.device_name}
        options={deviceOptions}
        onChange={(value?: string) => onFilterChange('device_name', value)}
      />
      <Select
        size="large"
        allowClear
        placeholder="Kết quả"
        className="!w-36"
        value={filters.result}
        options={RESULT_OPTIONS}
        onChange={(value?: string) => onFilterChange('result', value)}
      />
      {children}
      <Button variant="secondary" onClick={onReset}>
        Xoá lọc
      </Button>
    </div>
  );
}
