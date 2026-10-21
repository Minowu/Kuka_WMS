import { create } from 'zustand';
import type {
  RawMaterialPosition,
  PartModel,
  CncMachineStation,
  WashingSlot,
  PdaToastNotification,
} from '@/types/pda';
import {
  getPdaModelsApi,
  getPdaRawMaterialsApi,
  getPdaCncStationsApi,
  getPdaWashingSlotsApi,
  registerRawMaterialApi,
  callMaterialToCncApi,
  completeMachiningStageApi,
  returnEmptyCartFromWashingApi,
  simulateFastArriveApi,
} from '@/api/pda';
import { useAuthStore } from './useAuthStore';
import { getUserLocationsApi } from '@/api/machine';

// 7 Vị trí cấp phôi mặc định (fallback khi chưa kết nối backend)
const INITIAL_POSITIONS: RawMaterialPosition[] = [
  { id: 'RAW-01', locationId: 182, name: 'Khu Nguyên Liệu 01', hasRack: true, currentRackId: 'CART-001', currentModel: 'MODEL-A' },
  { id: 'RAW-02', locationId: 183, name: 'Khu Nguyên Liệu 02', hasRack: true, currentRackId: 'CART-002', currentModel: 'MODEL-A' },
  { id: 'RAW-03', locationId: 184, name: 'Khu Nguyên Liệu 03', hasRack: true, currentRackId: 'CART-003', currentModel: 'MODEL-B' },
  { id: 'RAW-04', locationId: 185, name: 'Khu Nguyên Liệu 04', hasRack: false },
  { id: 'RAW-05', locationId: 186, name: 'Khu Nguyên Liệu 05', hasRack: false },
  { id: 'RAW-06', locationId: 187, name: 'Khu Nguyên Liệu 06', hasRack: false },
  { id: 'RAW-07', locationId: 188, name: 'Khu Nguyên Liệu 07', hasRack: false },
];

// 7 Model sản phẩm mặc định
const INITIAL_MODELS: PartModel[] = [
  { id: 42, code: 'MODEL-A', name: 'Model A: Trục Chính CNC', description: 'Trục chính AMR - 3 Công đoạn' },
  { id: 43, code: 'MODEL-B', name: 'Model B: Mặt Bích CNC', description: 'Mặt bích hợp kim - 2 Công đoạn' },
];

// 8 Vị trí CNC (4 máy x 2 vị trí độc lập Vào & Ra - Double Buffering / Zero CNC Starvation)
const INITIAL_CNC_STATIONS: CncMachineStation[] = [
  // Máy CNC-01 (Level 1: Phay Thô)
  {
    id: 'CNC-01-POS1',
    locationId: 189,
    machineCode: 'CNC-01',
    positionIndex: 1,
    name: 'CNC-01 (Vị trí 1)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô',
    status: 'EMPTY',
    currentRack: null,
  },
  {
    id: 'CNC-01-POS2',
    locationId: 190,
    machineCode: 'CNC-01',
    positionIndex: 2,
    name: 'CNC-01 (Vị trí 2)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô',
    status: 'EMPTY',
    currentRack: null,
  },
  {
    id: 'CNC-01-POS3',
    locationId: 1901,
    machineCode: 'CNC-01',
    positionIndex: 3,
    name: 'CNC-01 (Vị trí 3)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô (Đệm)',
    status: 'EMPTY',
    currentRack: null,
  },
  // Máy CNC-02 (Level 1: Phay Thô Song Song)
  {
    id: 'CNC-02-POS1',
    locationId: 191,
    machineCode: 'CNC-02',
    positionIndex: 1,
    name: 'CNC-02 (Vị trí 1)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô (Song Song)',
    status: 'EMPTY',
    currentRack: null,
  },
  {
    id: 'CNC-02-POS2',
    locationId: 192,
    machineCode: 'CNC-02',
    positionIndex: 2,
    name: 'CNC-02 (Vị trí 2)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô (Song Song)',
    status: 'EMPTY',
    currentRack: null,
  },
  // Máy CNC-03 (Level 2: Phay Tinh)
  {
    id: 'CNC-03-POS1',
    locationId: 193,
    machineCode: 'CNC-03',
    positionIndex: 1,
    name: 'CNC-03 (Vị trí 1)',
    assignedStageLevel: 2,
    stageName: 'Phay Tinh',
    status: 'EMPTY',
    currentRack: null,
  },
  {
    id: 'CNC-03-POS2',
    locationId: 194,
    machineCode: 'CNC-03',
    positionIndex: 2,
    name: 'CNC-03 (Vị trí 2)',
    assignedStageLevel: 2,
    stageName: 'Phay Tinh',
    status: 'EMPTY',
    currentRack: null,
  },
  // Máy CNC-04 (Level 3: Khoan Tappi & Hoàn Tất CNC)
  {
    id: 'CNC-04-POS1',
    locationId: 195,
    machineCode: 'CNC-04',
    positionIndex: 1,
    name: 'CNC-04 (Vị trí 1)',
    assignedStageLevel: 3,
    stageName: 'Khoan Tappi & Hoàn Tất',
    status: 'EMPTY',
    currentRack: null,
  },
  {
    id: 'CNC-04-POS2',
    locationId: 196,
    machineCode: 'CNC-04',
    positionIndex: 2,
    name: 'CNC-04 (Vị trí 2)',
    assignedStageLevel: 3,
    stageName: 'Khoan Tappi & Hoàn Tất',
    status: 'EMPTY',
    currentRack: null,
  },
];

// 4 Slot Tẩy Rửa
const INITIAL_WASHING_SLOTS: WashingSlot[] = [
  { id: 1, locationId: 197, code: 'WASH-01', name: 'Slot 1', status: 'EMPTY', currentRack: null },
  { id: 2, locationId: 198, code: 'WASH-02', name: 'Slot 2', status: 'EMPTY', currentRack: null },
  { id: 3, locationId: 199, code: 'WASH-03', name: 'Slot 3', status: 'EMPTY', currentRack: null },
  { id: 4, locationId: 200, code: 'WASH-04', name: 'Slot 4', status: 'EMPTY', currentRack: null },
];

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
  callMaterialToCnc: (stationId: string, modelId: string) => Promise<void>;
  fastArriveCnc: (stationId: string) => Promise<void>;
  updateCncStageLevel: (stationId: string) => Promise<void>;

  // Luồng Tẩy Rửa
  releaseWashingSlot: (slotId: number) => Promise<void>;
  simulateArriveWashing: (slotId: number) => void;
}

export const usePdaStore = create<PdaState>((set, get) => ({
  positions: INITIAL_POSITIONS,
  models: INITIAL_MODELS,
  cncStations: INITIAL_CNC_STATIONS,
  washingSlots: INITIAL_WASHING_SLOTS,
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

      let finalRaw = rawMaterials.length > 0 ? rawMaterials : get().positions;
      let finalCnc = cncStations.length > 0 ? cncStations : get().cncStations;
      let finalWash = washingSlots.length > 0 ? washingSlots : get().washingSlots;

      // Lọc danh sách máy/ô hiển thị đúng theo các vị trí được phân quyền của tài khoản đăng nhập
      const user = useAuthStore.getState().user;
      const isAdmin = !!user?.access?.is_admin || (user?.roles || []).some((r) => r.name === 'admin');

      if (user && !isAdmin) {
        try {
          const assignedIds = await getUserLocationsApi(user.id);
          if (assignedIds && assignedIds.length > 0) {
            const assignedSet = new Set(assignedIds);
            const filteredRaw = finalRaw.filter((p) => p.locationId && assignedSet.has(p.locationId));
            const filteredCnc = finalCnc.filter((s) => s.locationId && assignedSet.has(s.locationId));
            const filteredWash = finalWash.filter((w) => w.locationId && assignedSet.has(w.locationId));

            if (filteredRaw.length > 0) finalRaw = filteredRaw;
            if (filteredCnc.length > 0) finalCnc = filteredCnc;
            if (filteredWash.length > 0) finalWash = filteredWash;
          }
        } catch {
          // Fallback gracefully if location API is unreachable
        }
      }

      set({
        models: models.length > 0 ? models : get().models,
        positions: finalRaw,
        cncStations: finalCnc,
        washingSlots: finalWash,
        loading: false,
        initialized: true,
      });
    } catch (error) {
      console.warn('PDA API connection unavailable, falling back to local store:', error);
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

  // 1. Cấp phôi từ khu nguyên liệu
  supplyRawMaterial: async ({ positionId, modelId, rackId }) => {
    const { positions, models, showToast, fetchFloorState } = get();
    const pos = positions.find((p) => p.id === positionId);
    const model = models.find((m) => String(m.id) === String(modelId) || m.code === modelId);
    const modelName = model ? model.name : modelId;

    if (pos && pos.locationId && model && model.id) {
      try {
        const res = await registerRawMaterialApi({
          location_id: pos.locationId,
          item_id: Number(model.id),
          container_code: rackId,
        });
        showToast(
          `Đã nạp rack [${res.container_code}] tại [${res.location_code}] thành công!`,
          'kuka'
        );
        await fetchFloorState();
        return;
      } catch (err: any) {
        const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi cấp phôi';
        showToast(`Lỗi cấp phôi: ${errorMsg}`, 'warning');
        return;
      }
    }

    // Fallback local mock
    set((state) => ({
      positions: state.positions.map((p) =>
        p.id === positionId
          ? {
              ...p,
              hasRack: true,
              currentRackId: rackId,
              currentModel: modelName,
            }
          : p
      ),
    }));
    showToast(`Đã cấp phôi [${rackId}] cho [${modelName}] tại [${positionId}]!`, 'kuka');
  },

  // 2. Gọi phôi đến trạm CNC
  callMaterialToCnc: async (stationId, modelId) => {
    const { cncStations, models, showToast, fetchFloorState } = get();
    const station = cncStations.find((s) => s.id === stationId);
    const model = models.find((m) => String(m.id) === String(modelId) || m.code === modelId);
    const modelName = model ? model.name : modelId;

    // Optimistic UI update
    set((state) => ({
      cncStations: state.cncStations.map((st) =>
        st.id === stationId
          ? { ...st, status: 'CALLING', callingModel: modelName }
          : st
      ),
    }));

    if (station && station.locationId && model && model.id) {
      try {
        await callMaterialToCncApi({
          destination_location_id: station.locationId,
          item_id: Number(model.id),
        });
        showToast(`Đã điều AMR chở [${modelName}] tới [${stationId}]`, 'kuka');
        await fetchFloorState();
        return;
      } catch (err: any) {
        const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi gọi phôi';
        showToast(`Lỗi gọi phôi: ${errorMsg}`, 'warning');
        await fetchFloorState();
        return;
      }
    }

    showToast(`Đã điều AMR chở [${modelName}] tới [${stationId}]`, 'kuka');

    // Fallback simulation if offline
    setTimeout(() => {
      const currentStations = get().cncStations;
      const target = currentStations.find((s) => s.id === stationId);
      if (target && target.status === 'CALLING') {
        const randomRackId = `RCK-${stationId}-${Math.floor(1000 + Math.random() * 9000)}`;
        const inputLevel = target.assignedStageLevel === 1 ? 0 : target.assignedStageLevel - 1;

        set((state) => ({
          cncStations: state.cncStations.map((st) =>
            st.id === stationId
              ? {
                  ...st,
                  status: 'OCCUPIED',
                  callingModel: undefined,
                  currentRack: {
                    rackId: randomRackId,
                    model: modelName,
                    level: inputLevel,
                    startedAt: new Date().toLocaleTimeString('vi-VN', {
                      hour: '2-digit',
                      minute: '2-digit',
                    }),
                  },
                }
              : st
          ),
        }));
        get().showToast(`AMR đã cập bến [${stationId}]: Phôi sẵn sàng gia công!`, 'success');
      }
    }, 3000);
  },

  fastArriveCnc: async (stationId) => {
    const { cncStations, showToast, fetchFloorState } = get();
    const station = cncStations.find((s) => s.id === stationId);

    if (station && station.locationId) {
      try {
        await simulateFastArriveApi({ station_id: stationId, location_id: station.locationId });
        showToast(`AMR đã cập bến [${stationId}] thành công!`, 'success');
        await fetchFloorState();
        return;
      } catch (err: any) {
        console.warn('API fast-arrive error, using mock fallback:', err);
      }
    }

    if (!station) return;
    const modelName = station.callingModel || 'Phôi tiêu chuẩn';
    const randomRackId = `RCK-${stationId}-${Math.floor(1000 + Math.random() * 9000)}`;
    const inputLevel = station.assignedStageLevel === 1 ? 0 : station.assignedStageLevel - 1;

    set((state) => ({
      cncStations: state.cncStations.map((st) =>
        st.id === stationId
          ? {
              ...st,
              status: 'OCCUPIED',
              callingModel: undefined,
              currentRack: {
                rackId: randomRackId,
                model: modelName,
                level: inputLevel,
                startedAt: new Date().toLocaleTimeString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                }),
              },
            }
          : st
      ),
    }));
    showToast(`AMR đã cập bến [${stationId}] thành công!`, 'success');
  },

  // 3. Cập nhật Level CNC
  updateCncStageLevel: async (stationId) => {
    const { cncStations, showToast, fetchFloorState } = get();
    const station = cncStations.find((s) => s.id === stationId);
    if (!station || !station.currentRack) return;

    const rackCode = station.currentRack.rackId;
    const targetLevel = station.assignedStageLevel;
    const isFinalStage = targetLevel >= 3;

    if (station.locationId) {
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
        return;
      } catch (err: any) {
        const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi cập nhật công đoạn';
        showToast(`Lỗi: ${errorMsg}`, 'warning');
        await fetchFloorState();
        return;
      }
    }

    // Fallback mock
    if (isFinalStage) {
      const finishedRack = {
        ...station.currentRack,
        level: targetLevel,
      };

      set((state) => ({
        cncStations: state.cncStations.map((st) =>
          st.id === stationId ? { ...st, status: 'EMPTY', currentRack: null } : st
        ),
      }));

      let slotAssigned = '';
      set((state) => {
        const slots = [...state.washingSlots];
        const emptyIdx = slots.findIndex((s) => s.status === 'EMPTY');
        const targetIdx = emptyIdx !== -1 ? emptyIdx : 0;
        slotAssigned = slots[targetIdx].name;

        slots[targetIdx] = {
          ...slots[targetIdx],
          status: 'OCCUPIED',
          currentRack: {
            rackId: finishedRack.rackId,
            model: finishedRack.model,
            fromStation: `Từ ${stationId}`,
            arrivedAt: new Date().toLocaleTimeString('vi-VN', {
              hour: '2-digit',
              minute: '2-digit',
            }),
          },
        };
        return { washingSlots: slots };
      });

      showToast(
        `Hoàn tất Level ${targetLevel} tại [${stationId}] -> AMR đã chở sang [${slotAssigned || 'Khu Tẩy Rửa'}]!`,
        'kuka'
      );
    } else {
      set((state) => ({
        cncStations: state.cncStations.map((st) =>
          st.id === stationId ? { ...st, status: 'EMPTY', currentRack: null } : st
        ),
      }));

      showToast(
        `Đã hoàn tất Level ${targetLevel} (${station.stageName}) tại [${stationId}]! Xe [${rackCode}] sẵn sàng cho Level ${targetLevel + 1}.`,
        'success'
      );
    }
  },

  // 4. Khu Tẩy Rửa: Giải phóng slot
  releaseWashingSlot: async (slotId) => {
    const { washingSlots, showToast, fetchFloorState } = get();
    const slot = washingSlots.find((s) => s.id === slotId);

    if (slot && slot.currentRack?.rackId) {
      try {
        await returnEmptyCartFromWashingApi({ container_code: slot.currentRack.rackId });
        showToast(`Đã giải phóng ${slot.name} (${slot.currentRack.rackId}) -> AMR đang đưa xe rỗng về bãi đệm!`, 'success');
        await fetchFloorState();
        return;
      } catch (err: any) {
        const errorMsg = err?.response?.data?.detail || err?.message || 'Lỗi giải phóng slot';
        showToast(`Lỗi: ${errorMsg}`, 'warning');
        await fetchFloorState();
        return;
      }
    }

    set((state) => ({
      washingSlots: state.washingSlots.map((s) =>
        s.id === slotId ? { ...s, status: 'EMPTY', currentRack: null } : s
      ),
    }));
    showToast(`Đã giải phóng Slot ${slotId} về TRỐNG!`, 'success');
  },

  simulateArriveWashing: (slotId) => {
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    set((state) => ({
      washingSlots: state.washingSlots.map((s) =>
        s.id === slotId
          ? {
              ...s,
              status: 'OCCUPIED',
              currentRack: {
                rackId: `RCK-CNC04-${randomSuffix}`,
                model: 'Model 3: Mặt Bích Động Cơ',
                fromStation: 'Từ CNC-04',
                arrivedAt: new Date().toLocaleTimeString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                }),
              },
            }
          : s
      ),
    }));
    get().showToast(`Mô phỏng: AMR đã hạ xe xuống Slot ${slotId}`, 'info');
  },
}));
