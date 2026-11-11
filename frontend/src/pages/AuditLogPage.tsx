import { Tabs } from 'antd';
import { Card } from '@/components/ui';
import ActionLogTab from './components/auditLog/ActionLogTab';
import AuditLogTab from './components/auditLog/AuditLogTab';

const TAB_ITEMS = [
  { key: 'audit', label: 'Đăng nhập & bảo mật', children: <AuditLogTab /> },
  { key: 'action', label: 'Thao tác nghiệp vụ', children: <ActionLogTab /> },
];

export default function AuditLogPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Nhật ký hệ thống</h1>
        <p className="text-slate-500 mt-1">
          Audit log (đăng nhập, phân quyền) và action log (thao tác thay đổi dữ liệu)
        </p>
      </div>
      <Card>
        <Tabs items={TAB_ITEMS} />
      </Card>
    </div>
  );
}
