import React, { useState, useMemo, useEffect } from 'react';
import { Modal, Button, Tag, Space, Alert, Typography, Select, Tooltip } from 'antd';
import {
  EnvironmentOutlined,
  CheckCircleOutlined,
  AimOutlined,
  StopOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import WarehouseMapCanvas from '@/components/shared/WarehouseMapCanvas';
import type { NodeInfo } from '@/types/warehouseMap';
import type { AvailableMapNode } from '@/types/station';

const { Text } = Typography;

export interface MapNodePickerModalProps {
  open: boolean;
  onClose: () => void;
  onSelectNode: (node: AvailableMapNode) => void;
  title?: string;
  currentSelectedNodeLabel?: string;
  availableNodes: AvailableMapNode[];
  assignedNodesMap: Map<string, { id?: number; name: string; zone: string }>;
  currentLocationId?: number | null;
  selectedInForm?: (string | undefined)[];
}

export const MapNodePickerModal: React.FC<MapNodePickerModalProps> = ({
  open,
  onClose,
  onSelectNode,
  title = 'Chọn điểm đỗ (Node Map) trên sơ đồ xưởng',
  currentSelectedNodeLabel,
  availableNodes,
  assignedNodesMap,
  currentLocationId,
  selectedInForm = [],
}) => {
  // Điểm đang được user tạm chọn trên bản đồ
  const [tempSelectedNode, setTempSelectedNode] = useState<AvailableMapNode | null>(null);
  const [validationMessage, setValidationMessage] = useState<{
    type: 'success' | 'warning' | 'error' | 'info';
    text: string;
  } | null>(null);

  // Helper tìm AvailableMapNode theo bất kỳ identifier nào (number, label, uuid, RACK_...)
  const findAvailableNode = useMemo(() => {
    return (rawKey?: string | number | null): AvailableMapNode | undefined => {
      if (!rawKey) return undefined;
      const str = String(rawKey).trim();
      const lower = str.toLowerCase();
      const clean = lower.replace(/^rack_|^chg_|^dock_/, '').trim();

      return availableNodes.find((n) => {
        const nNum = String(n.node_number).toLowerCase();
        const nLbl = String(n.node_label).toLowerCase();
        return (
          nNum === lower ||
          nLbl === lower ||
          nNum === clean ||
          nLbl === clean ||
          nLbl.endsWith(`-${clean}`)
        );
      });
    };
  }, [availableNodes]);

  // Set điểm ban đầu khi mở modal
  useEffect(() => {
    if (open) {
      if (currentSelectedNodeLabel) {
        const found = findAvailableNode(currentSelectedNodeLabel);
        setTempSelectedNode(found || null);
        if (found) {
          const assignedInfo =
            assignedNodesMap.get(String(found.node_label).toLowerCase()) ||
            assignedNodesMap.get(String(found.node_number).toLowerCase());
          const isAssignedToSelf = currentLocationId && assignedInfo?.id === currentLocationId;
          const statusText = isAssignedToSelf
            ? 'Đang gán cho trạm hiện tại'
            : assignedInfo
            ? `Đã gán cho ${assignedInfo.name} (${assignedInfo.zone})`
            : 'Điểm trống chưa gán';

          setValidationMessage({
            type: 'info',
            text: `Điểm hiện tại: Node ${found.node_number} (Tọa độ: X=${found.map_x}, Y=${found.map_y}) • Trạng thái: ${statusText}`,
          });
        } else {
          setValidationMessage(null);
        }
      } else {
        setTempSelectedNode(null);
        setValidationMessage(null);
      }
    }
  }, [open, currentSelectedNodeLabel, findAvailableNode, assignedNodesMap, currentLocationId]);

  // Kiểm tra tính hợp lệ của một Node
  const checkEligibility = (node: AvailableMapNode) => {
    const assignedInfo =
      assignedNodesMap.get(String(node.node_label).toLowerCase()) ||
      assignedNodesMap.get(String(node.node_number).toLowerCase());

    const isAssignedToSelf = currentLocationId && assignedInfo?.id === currentLocationId;

    // Đang được chọn ở slot khác trong cùng form máy CNC đa slot
    const isPickedInOtherSlot =
      selectedInForm.some(
        (sel) =>
          sel &&
          (String(sel).toLowerCase() === String(node.node_label).toLowerCase() ||
            String(sel).toLowerCase() === String(node.node_number).toLowerCase())
      ) &&
      String(node.node_label).toLowerCase() !== String(currentSelectedNodeLabel).toLowerCase() &&
      String(node.node_number).toLowerCase() !== String(currentSelectedNodeLabel).toLowerCase();

    if (isPickedInOtherSlot) {
      return {
        eligible: false,
        reason: `Node ${node.node_number} đang được chọn ở một vị trí khác trong form này.`,
        assignedInfo,
        isAssignedToSelf: false,
      };
    }

    if (assignedInfo && !isAssignedToSelf) {
      return {
        eligible: false,
        reason: `Node ${node.node_number} đã được gán cho '${assignedInfo.name}' (${assignedInfo.zone}). Không thể gán trùng cho 2 trạm.`,
        assignedInfo,
        isAssignedToSelf: false,
      };
    }

    return {
      eligible: true,
      reason: isAssignedToSelf
        ? `Node ${node.node_number} đang gán cho trạm hiện tại (Hợp lệ).`
        : `Node ${node.node_number} là điểm đỗ trống chưa gán (Hợp lệ).`,
      assignedInfo,
      isAssignedToSelf: !!isAssignedToSelf,
    };
  };

  // Xử lý khi user click vào một node trên Canvas
  const handleNodeClick = (clickedNode: NodeInfo | null) => {
    if (!clickedNode) {
      return;
    }

    const rawKey = clickedNode.content || clickedNode.name;
    const availableNode = findAvailableNode(rawKey);

    if (!availableNode) {
      setValidationMessage({
        type: 'warning',
        text: `Node ${rawKey} là điểm dẫn đường (waypoint), không phải điểm đỗ / kệ hàng (functionType=2). Vui lòng chọn các điểm kệ hình chữ nhật trên bản đồ.`,
      });
      return;
    }

    const check = checkEligibility(availableNode);
    setTempSelectedNode(availableNode);

    if (!check.eligible) {
      setValidationMessage({
        type: 'warning',
        text: check.reason,
      });
    } else {
      setValidationMessage({
        type: 'success',
        text: `Đã chọn Node ${availableNode.node_number} (Tọa độ: X=${availableNode.map_x}, Y=${availableNode.map_y}) • ${check.reason}`,
      });
    }
  };

  // Xử lý khi user chọn từ dropdown tìm kiếm nhanh
  const handleSelectFromDropdown = (nodeLabel: string) => {
    const node = findAvailableNode(nodeLabel);
    if (!node) return;
    const check = checkEligibility(node);
    setTempSelectedNode(node);
    if (!check.eligible) {
      setValidationMessage({
        type: 'warning',
        text: check.reason,
      });
    } else {
      setValidationMessage({
        type: 'success',
        text: `Đã chọn Node ${node.node_number} (Tọa độ: X=${node.map_x}, Y=${node.map_y}) • ${check.reason}`,
      });
    }
  };

  const handleConfirm = () => {
    if (tempSelectedNode) {
      const check = checkEligibility(tempSelectedNode);
      if (!check.eligible) {
        setValidationMessage({
          type: 'error',
          text: check.reason,
        });
        return;
      }
      onSelectNode(tempSelectedNode);
      onClose();
    }
  };

  // Tạo danh sách options cho ô tìm kiếm nhanh trên header
  const quickSelectOptions = useMemo(() => {
    return availableNodes.map((n) => {
      const assigned =
        assignedNodesMap.get(String(n.node_label).toLowerCase()) ||
        assignedNodesMap.get(String(n.node_number).toLowerCase());
      const isSelf = currentLocationId && assigned?.id === currentLocationId;
      let badge = '[Trống]';
      if (isSelf) {
        badge = `[Hiện tại: ${assigned?.name}]`;
      } else if (assigned) {
        badge = `[${assigned.name} - ${assigned.zone}]`;
      }

      return {
        value: n.node_label,
        label: `Node ${n.node_number} ${badge}`,
        node: n,
      };
    });
  }, [availableNodes, assignedNodesMap, currentLocationId]);

  // Danh sách tất cả các điểm CÓ THỂ CHỌN (Khả dụng) trên bản đồ để highlight
  const selectableLocationCodes = useMemo(() => {
    const list: string[] = [];
    const isOverviewMode = !currentLocationId && (!selectedInForm || selectedInForm.length === 0);

    availableNodes.forEach((node) => {
      if (isOverviewMode) {
        // Chế độ xem tổng quan toàn xưởng: highlight toàn bộ 50 điểm đỗ vật lý
        if (node.node_label) list.push(String(node.node_label));
        if (node.node_number) list.push(String(node.node_number));
      } else {
        // Chế độ chọn điểm cho form trạm: chỉ highlight các điểm hợp lệ (trống hoặc của chính trạm này)
        const check = checkEligibility(node);
        if (check.eligible) {
          if (node.node_label) list.push(String(node.node_label));
          if (node.node_number) list.push(String(node.node_number));
        }
      }
    });
    return list;
  }, [availableNodes, currentLocationId, selectedInForm, checkEligibility]);

  const currentSelectionEligibility = useMemo(() => {
    if (!tempSelectedNode) return null;
    return checkEligibility(tempSelectedNode);
  }, [tempSelectedNode, checkEligibility]);

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <div className="flex items-center justify-between pr-8">
          <div className="flex items-center gap-2">
            <EnvironmentOutlined className="text-brand-primary text-lg" />
            <span className="font-bold text-slate-800">{title}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-normal">
              🔍 Tìm nhanh điểm đỗ:
            </span>
            <Select
              showSearch
              placeholder="Gõ số Node (vd: 20, 216...)"
              value={tempSelectedNode?.node_label}
              onChange={handleSelectFromDropdown}
              options={quickSelectOptions}
              filterOption={(input, option) =>
                (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
              }
              className="w-64 text-xs"
              size="small"
              allowClear
            />
          </div>
        </div>
      }
      width="90vw"
      style={{ top: 20 }}
      styles={{
        body: {
          padding: 0,
          height: 'calc(85vh - 110px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          backgroundColor: '#f8fafc',
        },
      }}
      footer={
        <div className="flex items-center justify-between px-4 py-2 bg-white border-t border-slate-200">
          <div className="flex items-center gap-2">
            {tempSelectedNode ? (
              <div className="flex items-center gap-2">
                <Tag
                  color={currentSelectionEligibility?.eligible ? 'cyan' : 'orange'}
                  className="text-xs font-semibold py-1 px-2.5 flex items-center gap-1"
                >
                  {currentSelectionEligibility?.eligible ? (
                    <CheckCircleOutlined className="text-emerald-500" />
                  ) : (
                    <StopOutlined className="text-amber-500" />
                  )}
                  Đang chọn: Node {tempSelectedNode.node_number} (Tọa độ: X={tempSelectedNode.map_x}, Y={tempSelectedNode.map_y})
                </Tag>
                {currentSelectionEligibility?.assignedInfo && !currentSelectionEligibility.isAssignedToSelf && (
                  <Tag color="error" className="text-xs">
                    Thuộc: {currentSelectionEligibility.assignedInfo.name} ({currentSelectionEligibility.assignedInfo.zone})
                  </Tag>
                )}
              </div>
            ) : (
              <Text type="secondary" className="text-xs flex items-center gap-1">
                <AimOutlined className="text-brand-primary" />
                Nhấp chuột vào bất kỳ điểm kệ đỗ (hình chữ nhật) trên bản đồ để chọn
              </Text>
            )}
          </div>

          <Space>
            <Button onClick={onClose}>Đóng</Button>
            <Tooltip
              title={
                !tempSelectedNode
                  ? 'Vui lòng chọn 1 điểm đỗ'
                  : !currentSelectionEligibility?.eligible
                  ? currentSelectionEligibility?.reason
                  : undefined
              }
            >
              <Button
                type="primary"
                disabled={!tempSelectedNode || !currentSelectionEligibility?.eligible}
                onClick={handleConfirm}
                className="!bg-brand-primary hover:!bg-stripe-primary-deep font-semibold"
              >
                Xác nhận chọn Node
              </Button>
            </Tooltip>
          </Space>
        </div>
      }
      destroyOnHidden
    >
      {/* Thông báo xác nhận điểm vừa click (nếu có lỗi / thành công / hướng dẫn) */}
      {validationMessage && (
        <div className="px-4 py-1.5 shrink-0 bg-slate-50 border-b border-slate-200">
          <Alert
            type={validationMessage.type}
            message={validationMessage.text}
            showIcon
            closable
            className="text-xs !py-1 !px-3 shadow-xs"
          />
        </div>
      )}

      {/* Tái sử dụng WarehouseMapCanvas nguyên bản với đầy đủ hình họa chuẩn và Highlight điểm khả dụng */}
      <div className="flex-1 relative w-full h-full min-h-0 bg-transparent overflow-hidden">
        <WarehouseMapCanvas
          hideToolbar={true}
          hideDrawer={true}
          selectableLocationCodes={selectableLocationCodes}
          selectedLocationCodes={
            tempSelectedNode
              ? [
                  String(tempSelectedNode.node_label),
                  String(tempSelectedNode.node_number),
                ]
              : []
          }
          onNodeClick={handleNodeClick}
        />
      </div>
    </Modal>
  );
};

export default MapNodePickerModal;
