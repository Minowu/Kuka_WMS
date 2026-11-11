import dayjs from 'dayjs';
import type { ColumnType } from 'antd/es/table';
import { DEVICE_TYPE_LABELS } from '@/constants/auditLog';
import type { DeviceType, LogResult } from '@/types/auditLog';
import LogResultTag from './LogResultTag';

interface CommonLogRow {
  created_at: string;
  username: string | null;
  ip: string | null;
  device_type: DeviceType | null;
  device_name: string | null;
  result: LogResult;
}

export function timeColumn<T extends CommonLogRow>(): ColumnType<T> {
  return {
    title: 'Thời gian',
    dataIndex: 'created_at',
    key: 'created_at',
    width: 170,
    render: (value: string) => dayjs(value).format('DD/MM/YYYY HH:mm:ss'),
  };
}

export function userColumn<T extends CommonLogRow>(): ColumnType<T> {
  return {
    title: 'Người dùng',
    dataIndex: 'username',
    key: 'username',
    width: 140,
    render: (value: string | null) => value ?? '—',
  };
}

export function deviceColumn<T extends CommonLogRow>(): ColumnType<T> {
  return {
    title: 'Thiết bị / IP',
    key: 'device',
    width: 180,
    render: (_value, record) => (
      <div className="flex flex-col leading-tight">
        <span className="font-medium text-slate-700">
          {record.device_name ?? (record.device_type ? DEVICE_TYPE_LABELS[record.device_type] : '—')}
        </span>
        <span className="text-xs text-slate-500">{record.ip ?? '—'}</span>
      </div>
    ),
  };
}

export function resultColumn<T extends CommonLogRow>(): ColumnType<T> {
  return {
    title: 'Kết quả',
    dataIndex: 'result',
    key: 'result',
    width: 110,
    render: (value: LogResult) => <LogResultTag result={value} />,
  };
}
