import { Tag } from 'antd';
import { LOG_RESULT_LABELS } from '@/constants/auditLog';
import type { LogResult } from '@/types/auditLog';

export default function LogResultTag({ result }: { result: LogResult }) {
  return (
    <Tag color={result === 'SUCCESS' ? 'green' : 'red'} className="!m-0">
      {LOG_RESULT_LABELS[result] ?? result}
    </Tag>
  );
}
