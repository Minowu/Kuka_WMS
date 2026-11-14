import { Alert, Spin } from 'antd';
import { ClusterOutlined } from '@ant-design/icons';
import { Modal } from '@/components/ui';
import type { User } from '@/types/auth';
import { useStationAssignment } from './stationAssignment/useStationAssignment';
import { LOCATION_GRID_THEMES } from './stationAssignment/stationAssignmentConfig';
import AreaSelector from './stationAssignment/AreaSelector';
import LocationCheckGrid from './stationAssignment/LocationCheckGrid';
import CncMachineCheckList from './stationAssignment/CncMachineCheckList';
import AssignmentFooter from './stationAssignment/AssignmentFooter';

interface StationAssignmentModalProps {
  open: boolean;
  onClose: () => void;
  user: User | null;
}

export default function StationAssignmentModal({ open, onClose, user }: StationAssignmentModalProps) {
  const assignment = useStationAssignment({ open, user, onClose });
  const { catalog, selectedArea, selectedSet } = assignment;

  const renderAreaDetail = () => {
    if (!catalog) return null;

    if (selectedArea === 'cnc') {
      return (
        <CncMachineCheckList
          machines={catalog.machines || []}
          selectedSet={selectedSet}
          onToggleMachine={assignment.toggleMachine}
          onSelectAll={assignment.selectAll}
          onClear={assignment.clearAll}
        />
      );
    }

    return (
      <LocationCheckGrid
        theme={LOCATION_GRID_THEMES[selectedArea]}
        items={(selectedArea === 'raw_material' ? catalog.raw_materials : catalog.washing_slots) || []}
        selectedSet={selectedSet}
        onToggle={assignment.toggleLocation}
        onSelectAll={assignment.selectAll}
        onClear={assignment.clearAll}
      />
    );
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-2 text-slate-800">
          <ClusterOutlined className="text-brand-primary text-xl" />
          <span>
            Phân Quyền Trạm Sản Xuất — <span className="text-brand-primary font-bold">{user?.username}</span>
          </span>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={
        <AssignmentFooter
          selectedArea={selectedArea}
          selectedCount={assignment.selectedIds.length}
          isSaving={assignment.isSaving}
          onCancel={onClose}
          onSave={assignment.save}
        />
      }
      centered
      width={760}
      className="[&_.ant-modal-content]:!rounded-2xl"
    >
      {assignment.isLoading ? (
        <div className="flex flex-col h-72 items-center justify-center gap-3">
          <Spin size="large" />
          <span className="text-slate-500 text-sm">Đang tải danh mục trạm xưởng...</span>
        </div>
      ) : !catalog ? (
        <div className="p-4 text-red-500">Không thể tải danh mục trạm xưởng.</div>
      ) : (
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1 py-1">
          <Alert
            type="info"
            showIcon
            title="Nguyên tắc 1 Tài khoản = 1 Khu vực duy nhất"
            description="Mỗi nhân viên chỉ trực tại đúng 1 khu vực sản xuất. Khi chuyển khu vực, hệ thống sẽ tự động phân công vị trí theo khu vực mới và giải phóng quyền ở các khu vực khác."
            className="rounded-xl text-xs"
          />

          <div>
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">
              Tầng 1: Chọn Phân Khu Sản Xuất Trực Thuộc
            </div>
            <AreaSelector
              catalog={catalog}
              value={selectedArea}
              roleArea={assignment.roleArea}
              onChange={assignment.changeArea}
            />
          </div>

          <div className="border border-slate-200/90 rounded-xl p-4 bg-slate-50/40 space-y-3">
            {renderAreaDetail()}
          </div>
        </div>
      )}
    </Modal>
  );
}
