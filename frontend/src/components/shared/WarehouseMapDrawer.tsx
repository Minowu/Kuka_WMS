import React from 'react';
import { useLocationDetail } from '@/hooks/useWarehouseMap';
import { Loading, Alert, Button } from '@/components/ui';
import { cn } from '@/components/ui/utils/cn';
import { formatQuantity } from '@/utils/formatQuantity';

interface NodeInfo {
  x: number;
  y: number;
  type: number;
  content: string;
  name: string;
}

interface WarehouseMapDrawerProps {
  visible: boolean;
  onClose: () => void;
  node: NodeInfo | null;
  locationId?: number;
  refreshToken?: number;
}

const LOCATION_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  CNC_SLOT: { label: 'Trạm Máy CNC', color: 'bg-blue-100 text-blue-800 border-blue-200' },
  RAW_MATERIAL: { label: 'Kho Phôi Thô', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  WASHING_SLOT: { label: 'Trạm Tẩy Rửa', color: 'bg-purple-100 text-purple-800 border-purple-200' },
  EMPTY_CART_BUFFER: { label: 'Đệm Xe Rỗng', color: 'bg-amber-100 text-amber-800 border-amber-200' },
  UNASSIGNED: { label: 'Chưa phân khu', color: 'bg-slate-100 text-slate-700 border-slate-200' },
};

const WarehouseMapDrawer: React.FC<WarehouseMapDrawerProps> = ({
  visible,
  onClose,
  node,
  locationId,
  refreshToken = 0,
}) => {
  const {
    data: detailData,
    isLoading,
    isFetching,
    isError,
  } = useLocationDetail(
    node?.type === 1 ? locationId : undefined,
    refreshToken,
  );

  const location = detailData?.location;
  const locType = location?.location_type || 'UNASSIGNED';
  const typeMeta = LOCATION_TYPE_LABELS[locType] || LOCATION_TYPE_LABELS.UNASSIGNED;

  const modelName = detailData?.model_name || detailData?.item_stock?.[0]?.sku;
  const rawQty = detailData?.quantity || detailData?.item_stock?.[0]?.quantity;
  const displayQty = rawQty ? formatQuantity(rawQty, '0') : null;
  const containerCode = detailData?.container_code;
  const stageName = detailData?.stage_name;
  const transitInfo = detailData?.transit_info;
  const hasContent = Boolean(modelName || containerCode || (detailData && detailData.summary.item_stock_count > 0));

  return (
    <>
      {visible && (
        <div
          className="absolute inset-0 z-40 bg-slate-900/20 backdrop-blur-[1px] transition-opacity"
          onClick={onClose}
        />
      )}

      <div
        className={cn(
          "absolute top-0 right-0 bottom-0 z-50 w-full max-w-md bg-white shadow-2xl border-l border-slate-200 transform transition-transform duration-300 ease-in-out flex flex-col font-sans",
          visible ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-slate-50/80">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-slate-800">
                {location?.location_name || node?.name || 'Chi tiết vị trí'}
              </h3>
              <span className={cn('px-2 py-0.5 text-xs font-semibold rounded-full border', typeMeta.color)}>
                {typeMeta.label}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium mt-1">
              Mã vị trí: <span className="font-mono text-slate-700">{location?.location_code || node?.content}</span>
            </p>
          </div>
          <Button
            variant="text"
            onClick={onClose}
            className="!p-2 !w-9 !h-9 !rounded-full !text-slate-400 hover:!bg-slate-200 hover:!text-slate-700 flex items-center justify-center cursor-pointer"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </Button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {isFetching && !isLoading && detailData ? (
            <p className="text-center text-xs text-slate-400">Đang đồng bộ dữ liệu mới nhất...</p>
          ) : null}

          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-48">
              <Loading text="Đang tải thông tin trạm..." className="!h-auto" />
            </div>
          ) : isError ? (
            <Alert variant="error" className="w-full text-center">
              Không thể tải thông tin chi tiết của vị trí này.
            </Alert>
          ) : detailData ? (
            <>
              {/* Thẻ 1: Vị trí & Trạm máy */}
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 shadow-sm">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Thông tin Trạm Máy
                </h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="block text-xs text-slate-500">Tên trạm / Vị trí</span>
                    <span className="font-semibold text-slate-800">
                      {location?.location_name || '-'}
                    </span>
                  </div>
                  <div>
                    <span className="block text-xs text-slate-500">Máy phụ trách</span>
                    <span className="font-semibold text-slate-800">
                      {detailData.machine_code ? `${detailData.machine_code} (${detailData.machine_name || ''})` : '—'}
                    </span>
                  </div>
                  {detailData.position_name && (
                    <div>
                      <span className="block text-xs text-slate-500">Điểm đệm máy</span>
                      <span className="font-semibold text-brand-primary">
                        {detailData.position_name}
                      </span>
                    </div>
                  )}
                  <div>
                    <span className="block text-xs text-slate-500">Trạng thái điểm</span>
                    <span className={cn(
                      'font-semibold capitalize',
                      location?.status === 'has_stock' ? 'text-emerald-600' :
                      location?.status === 'reserved' ? 'text-amber-600' :
                      location?.status === 'in_transit' ? 'text-blue-600' : 'text-slate-500'
                    )}>
                      {location?.status === 'has_stock' ? 'Đang có phôi' :
                       location?.status === 'reserved' ? 'Đang giữ chỗ' :
                       location?.status === 'in_transit' ? 'Đang luân chuyển' : 'Vị trí trống'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Thẻ 2: Model Sản phẩm & Xe phôi đang ở đây */}
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                  Hàng hóa & Xe Phôi
                </h4>

                {hasContent ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <div>
                        <span className="text-xs text-slate-400 block">Model sản phẩm</span>
                        <span className="text-xl font-bold text-slate-800">
                          {modelName || 'Chưa định danh Model'}
                        </span>
                      </div>
                      {displayQty && (
                        <div className="text-right">
                          <span className="text-xs text-slate-400 block">Số lượng</span>
                          <span className="text-xl font-extrabold text-emerald-600">
                            {displayQty} <span className="text-xs font-normal text-slate-500">pcs</span>
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="block text-xs text-slate-500">Mã xe gá phôi</span>
                        <span className="font-mono font-bold text-brand-dark">
                          {containerCode || '—'}
                        </span>
                      </div>
                      <div>
                        <span className="block text-xs text-slate-500">Công đoạn gia công</span>
                        <span className="font-semibold text-slate-700">
                          {stageName || (detailData.current_stage_level != null ? `Công đoạn ${detailData.current_stage_level}` : '—')}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-dashed border-slate-200 rounded-lg text-center">
                    <p className="text-sm font-medium text-slate-600">Vị trí hiện đang trống</p>
                    <p className="text-xs text-slate-400 mt-1">Sẵn sàng tiếp nhận xe phôi hoặc lệnh cấp hàng</p>
                  </div>
                )}
              </div>

              {/* Thẻ 3: Thông tin luân chuyển nếu đang có nhiệm vụ vận chuyển */}
              {(transitInfo || location?.status === 'reserved' || location?.status === 'in_transit') && (
                <div className="rounded-xl border border-blue-200 bg-blue-50/70 p-4 shadow-sm">
                  <h4 className="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                    <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                    Trạng Thái Luân Chuyển AMR
                  </h4>
                  <p className="text-sm font-semibold text-blue-900 mt-1">
                    {transitInfo || (
                      location?.status === 'reserved'
                        ? 'Vị trí này đang được giữ chỗ cho nhiệm vụ AMR kế tiếp.'
                        : 'Xe phôi tại vị trí này đang được khóa cho nhiệm vụ vận chuyển.'
                    )}
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-center p-6">
              <p className="text-sm font-medium text-slate-600">
                Không tìm thấy thông tin cấu hình cho Node này.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default WarehouseMapDrawer;
