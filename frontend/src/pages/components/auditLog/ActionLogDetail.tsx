import type { ActionLog } from '@/types/auditLog';
import JsonBlock from './JsonBlock';

export default function ActionLogDetail({ record }: { record: ActionLog }) {
  return (
    <div className="space-y-3 text-left">
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-600">
        <span>
          Route: <span className="font-mono">{record.route_template ?? '—'}</span>
        </span>
        <span>
          Request ID: <span className="font-mono">{record.request_id ?? '—'}</span>
        </span>
        <span>Thời gian xử lý: {record.duration_ms ?? '—'} ms</span>
      </div>
      {record.error_message && (
        <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{record.error_message}</div>
      )}
      <div className="flex flex-wrap gap-3">
        <JsonBlock title="Payload" value={record.payload} />
        <JsonBlock title="Query params" value={record.query_params} />
      </div>
    </div>
  );
}
