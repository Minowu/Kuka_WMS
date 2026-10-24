import { create } from 'zustand';
import type {
  CncMachineStation,
  PartModel,
  PdaToastNotification,
  RawMaterialPosition,
  WashingSlot,
} from '@/types/pda';
import {
  callMaterialToCncApi,
  getPdaCncStationsApi,
  getPdaModelsApi,
  getPdaRawMaterialsApi,
  getPdaWashingSlotsApi,
  registerRawMaterialApi,
  completeMachiningStageApi,
  returnEmptyCartFromWashingApi,
} from '@/api/pda';
import { useAuthStore } from './useAuthStore';
import { getUserLocationsApi } from '@/api/machine';

interface PdaState {
  positions: RawMaterialPosition[];
  models: PartModel[];
  cncStations: CncMachineStation[];
  washingSlots: WashingSlot[];
  toast: PdaToastNotification | null;
  loading: boolean;
  initialized: boolean;

  fetchFloorState: () => Promise<void>;
  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
  hideToast: () => void;

  // Luồng Nguyên Liệu
  supplyRawMaterial: (data: { positionId: string; modelId: string; rackId: string }) => Promise<void>;

  // Luồng CNC
  callMaterialToCnc: (stationId: string, itemId: number) => Promise<void>;
  updateCncStageLevel: (stationId: string) => Promise<void>;

  // Luồng Tẩy Rửa
  releaseWashingSlot: (slotId: number) => Promise<void>;
}

export const usePdaStore = create<PdaState>((set, get) => ({
  positions: [],
  models: [],
  cncStations: [],
  washingSlots: [],
  toast: null,
  loading: false,
  initialized: false,

  fetchFloorState: async () => {
    set({ loading: true });
    try {
      const [models, rawMaterials, cncStations, washingSlots] = await Promise.all([
        getPdaModelsApi(),
        getPdaRawMaterialsApi(),
        getPdaCncStationsApi(),
        getPdaWashingSlotsApi(),
      ]);

      set({
        models,
        positions: rawMaterials,
        cncStations,
        washingSlots,
        loading: false,
        initialized: true,
      });
    } catch (error) {
      console.warn('PDA API connection unavailable:', error);
      set({ loading: false, initialized: true });
    }
  },

  showToast: (message, type = 'kuka') => {
    set({
      toast: {
        id: `toast-${Date.now()}`,
        message,
        type,
        timestamp: Date.now(),
      },
    });
  },

  hideToast: () => set({ toast: null }),

  // 1. Cấp phôi tại vị trí nguyên liệu (Quét QR Rack thật)
  supplyRawMaterial: async ({ positionId, modelId, rackId }) => {
    const { positions, models, showToast, fetchFloorState } = get();
    const pos = positions.find((p) => p.id === positionId);
    const model = models.find((m) => String(m.id) === String(modelId) || m.code === modelId);

    if (!pos || !pos.locationId) {
      showToast('Vị trí cấp phôi không hợp lệ hoặc chưa liên kết tọa độ!', 'warning');
      return;
    }

    if (!model || !model.id) {
      showToast('Model phôi không hợp lệ!', 'warning');
      return;
    }

    if (!rackId || !rackId.trim()) {
      showToast('Vui lòng quét hoặc nhập mã khay phôi!', 'warning');
      return;
    }

    try {
      const res = await registerRawMaterialApi({
        location_id: pos.locationId,
        item_id: Number(model.id),
        container_code: rackId.trim(),
      });
      showToast(
        `Đã nạp rack [${res.container_code}] tại [${res.location_code}] thành công!`,
        'kuka'
      );
      await fetchFloorState();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi cấp phôi';
      showToast(`Lỗi cấp phôi: ${errorMsg}`, 'warning');
    }
  },

  // 2. Gọi phôi đến trạm CNC (ADR-002: Gọi phôi kèm Model ID đã chọn)
  callMaterialToCnc: async (stationId, itemId) => {
    const { cncStations, models, showToast, fetchFloorState } = get();
    const station = cncStations.find((s) => s.id === stationId);

    if (!station || !station.locationId) {
      showToast('Trạm CNC không hợp lệ hoặc chưa liên kết tọa độ!', 'warning');
      return;
    }

    if (!itemId) {
      showToast('Vui lòng chọn Model sản phẩm cần gọi!', 'warning');
      return;
    }

    const supported = station.supportedModels?.find((m) => m.itemId === itemId);
    const model = models.find((m) => Number(m.id) === itemId || Number(m.itemId) === itemId);
    const modelLabel = supported ? `${supported.modelCode} (${supported.modelName})` : (model?.name || `Model #${itemId}`);

    // Optimistic UI update
    set((state) => ({
      cncStations: state.cncStations.map((st) =>
        st.id === stationId
          ? {
              ...st,
              status: 'CALLING',
              callingModel: modelLabel,
            }
          : st
      ),
    }));

    try {
      await callMaterialToCncApi({
        destination_location_id: station.locationId,
        item_id: itemId,
      });
      showToast(`Đã điều AMR chở [${modelLabel}] tới [${station.name}]`, 'kuka');
      await fetchFloorState();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi gọi phôi';
      showToast(`Lỗi gọi phôi: ${errorMsg}`, 'warning');
      await fetchFloorState();
    }
  },

  // 3. Hoàn tất công đoạn CNC -> Kích hoạt điều phối AMR tự động
  updateCncStageLevel: async (stationId) => {
    const { cncStations, showToast, fetchFloorState } = get();
    const station = cncStations.find((s) => s.id === stationId);

    if (!station || !station.locationId) {
      showToast('Trạm CNC không hợp lệ hoặc chưa liên kết tọa độ!', 'warning');
      return;
    }

    const currentLevel = station.currentRack?.level ?? 0;
    const targetLevel = currentLevel + 1;
    const isFinalStage = Boolean(station.isFinalStep);
    const rackCode = station.currentRack?.rackId;

    if (!rackCode) {
      showToast('Không tìm thấy khay phôi tại trạm để báo hoàn tất!', 'warning');
      return;
    }

    try {
      await completeMachiningStageApi({
        container_code: rackCode,
        location_id: station.locationId,
      });
      if (isFinalStage) {
        showToast(
          `Hoàn tất Level ${targetLevel} tại [${stationId}] -> AMR đã nhận lệnh chuyển sang Khu Tẩy Rửa!`,
          'kuka'
        );
      } else {
        showToast(
          `Đã hoàn tất Level ${targetLevel} (${station.stageName}) tại [${stationId}]! Xe [${rackCode}] sẵn sàng cho bước sau.`,
          'success'
        );
      }
      await fetchFloorState();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi cập nhật công đoạn';
      showToast(`Lỗi: ${errorMsg}`, 'warning');
      await fetchFloorState();
    }
  },

  // 4. Khu Tẩy Rửa: Giải phóng slot
  releaseWashingSlot: async (slotId) => {
    const { washingSlots, showToast, fetchFloorState } = get();
    const slot = washingSlots.find((s) => s.id === slotId);

    if (!slot || !slot.currentRack?.rackId) {
      showToast('Slot này không có khay phôi để giải phóng!', 'warning');
      return;
    }

    try {
      await returnEmptyCartFromWashingApi({ container_code: slot.currentRack.rackId });
      showToast(`Đã giải phóng ${slot.name} (${slot.currentRack.rackId}) -> AMR đang đưa xe rỗng về bãi đệm!`, 'success');
      await fetchFloorState();
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi giải phóng slot';
      showToast(`Lỗi: ${errorMsg}`, 'warning');
      await fetchFloorState();
    }
  },
}));
