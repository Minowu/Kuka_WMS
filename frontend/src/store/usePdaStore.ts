import { create } from 'zustand';
import type {
  RawMaterialPosition,
  PartModel,
  CncMachineStation,
  WashingSlot,
  PdaToastNotification,
} from '@/types/pda';

// 7 Vị trí cấp phôi
const INITIAL_POSITIONS: RawMaterialPosition[] = [
  { id: 'VT-01', name: 'Vị trí 01', hasRack: true, currentRackId: 'RCK-VT01-1021', currentModel: 'Model 1' },
  { id: 'VT-02', name: 'Vị trí 02', hasRack: true, currentRackId: 'RCK-VT02-4412', currentModel: 'Model 2' },
  { id: 'VT-03', name: 'Vị trí 03', hasRack: false },
  { id: 'VT-04', name: 'Vị trí 04', hasRack: true, currentRackId: 'RCK-VT04-7729', currentModel: 'Model 3' },
  { id: 'VT-05', name: 'Vị trí 05', hasRack: false },
  { id: 'VT-06', name: 'Vị trí 06', hasRack: false },
  { id: 'VT-07', name: 'Vị trí 07', hasRack: false },
];

// 7 Model sản phẩm
const INITIAL_MODELS: PartModel[] = [
  { id: 'model-1', code: 'MDL-01', name: 'Model 1: Trục Rotor', description: 'Trục động cơ chính AMR' },
  { id: 'model-2', code: 'MDL-02', name: 'Model 2: Hộp Giảm Tốc', description: 'Vỏ hộp số bánh răng hành tinh' },
  { id: 'model-3', code: 'MDL-03', name: 'Model 3: Mặt Bích Động Cơ', description: 'Bích gá tiêu chuẩn KUKA' },
  { id: 'model-4', code: 'MDL-04', name: 'Model 4: Giá Đỡ Bánh Xe', description: 'Khung gầm chịu tải 1500kg' },
  { id: 'model-5', code: 'MDL-05', name: 'Model 5: Khớp Cánh Tay 1', description: 'Khớp xoay trục J1 hợp kim' },
  { id: 'model-6', code: 'MDL-06', name: 'Model 6: Khớp Cánh Tay 2', description: 'Khớp nâng trục J2 chịu lực' },
  { id: 'model-7', code: 'MDL-07', name: 'Model 7: Bàn Nâng AMR', description: 'Mặt bàn nâng thủy lực tích hợp' },
];

// 8 Vị trí CNC (4 máy x 2 vị trí độc lập Vào & Ra - Double Buffering / Zero CNC Starvation)
const INITIAL_CNC_STATIONS: CncMachineStation[] = [
  // Máy CNC-01 (Level 1: Phay Thô)
  {
    id: 'CNC01_POS1',
    machineCode: 'CNC-01',
    positionIndex: 1,
    name: 'CNC-01 (Vị trí 1)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô',
    status: 'EMPTY',
    currentRack: null,
  },
  {
    id: 'CNC01_POS2',
    machineCode: 'CNC-01',
    positionIndex: 2,
    name: 'CNC-01 (Vị trí 2)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô',
    status: 'EMPTY',
    currentRack: null,
  },
  // Máy CNC-02 (Level 1: Phay Thô Song Song)
  {
    id: 'CNC02_POS1',
    machineCode: 'CNC-02',
    positionIndex: 1,
    name: 'CNC-02 (Vị trí 1)',
    assignedStageLevel: 1,
    stageName: 'Phay Thô (Song Song)',
    status: 'OCCUPIED',
    currentRack: {
      rackId: 'RCK-VT01-1021',
      model: 'Model 1: Trục Rotor',
      level: 0, // Nhận phôi thô từ Nguyên liệu, chuẩn bị gia công lên Level 1
      startedAt: '10:05',
    },
  },
  {
    id: 'CNC02_POS2',
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
    id: 'CNC03_POS1',
    machineCode: 'CNC-03',
    positionIndex: 1,
    name: 'CNC-03 (Vị trí 1)',
    assignedStageLevel: 2,
    stageName: 'Phay Tinh',
    status: 'OCCUPIED',
    currentRack: {
      rackId: 'RCK-VT02-4412',
      model: 'Model 2: Hộp Giảm Tốc',
      level: 1, // Nhận phôi đã xong B1 (Level 1), chuẩn bị gia công lên Level 2
      startedAt: '09:40',
    },
  },
  {
    id: 'CNC03_POS2',
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
    id: 'CNC04_POS1',
    machineCode: 'CNC-04',
    positionIndex: 1,
    name: 'CNC-04 (Vị trí 1)',
    assignedStageLevel: 3,
    stageName: 'Khoan Tappi & Hoàn Tất',
    status: 'OCCUPIED',
    currentRack: {
      rackId: 'RCK-VT04-7729',
      model: 'Model 3: Mặt Bích Động Cơ',
      level: 2, // Nhận phôi đã xong B2 (Level 2), chuẩn bị gia công lên Level 3
      startedAt: '09:15',
    },
  },
  {
    id: 'CNC04_POS2',
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
  {
    id: 1,
    name: 'Slot 1',
    status: 'OCCUPIED',
    currentRack: {
      rackId: 'RCK-VT07-3310',
      model: 'Model 4: Giá Đỡ Động Cơ',
      fromStation: 'Từ CNC-04',
      arrivedAt: '10:12',
    },
  },
  { id: 2, name: 'Slot 2', status: 'EMPTY', currentRack: null },
  { id: 3, name: 'Slot 3', status: 'EMPTY', currentRack: null },
  { id: 4, name: 'Slot 4', status: 'EMPTY', currentRack: null },
];

interface PdaState {
  positions: RawMaterialPosition[];
  models: PartModel[];
  cncStations: CncMachineStation[];
  washingSlots: WashingSlot[];
  toast: PdaToastNotification | null;

  showToast: (msg: string, type?: 'success' | 'info' | 'warning' | 'kuka') => void;
  hideToast: () => void;

  // Luồng Nguyên Liệu
  supplyRawMaterial: (data: { positionId: string; modelId: string; rackId: string }) => void;

  // Luồng CNC
  callMaterialToCnc: (stationId: string, modelId: string) => void;
  fastArriveCnc: (stationId: string) => void;
  updateCncStageLevel: (stationId: string) => void;

  // Luồng Tẩy Rửa
  releaseWashingSlot: (slotId: number) => void;
  simulateArriveWashing: (slotId: number) => void;
}

export const usePdaStore = create<PdaState>((set, get) => ({
  positions: INITIAL_POSITIONS,
  models: INITIAL_MODELS,
  cncStations: INITIAL_CNC_STATIONS,
  washingSlots: INITIAL_WASHING_SLOTS,
  toast: null,

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
  supplyRawMaterial: ({ positionId, modelId, rackId }) => {
    const { models, showToast } = get();
    const model = models.find((m) => m.id === modelId);
    const modelName = model ? model.name : modelId;

    set((state) => ({
      positions: state.positions.map((pos) =>
        pos.id === positionId
          ? {
              ...pos,
              hasRack: true,
              currentRackId: rackId,
              currentModel: modelName,
            }
          : pos
      ),
    }));

    showToast(`Đã cấp phôi [${rackId}] cho [${modelName}] tại [${positionId}]!`, 'kuka');
  },

  // 2. Gọi phôi đến trạm CNC
  callMaterialToCnc: (stationId, modelId) => {
    const { models, showToast } = get();
    const model = models.find((m) => m.id === modelId);
    const modelName = model ? model.name : modelId;

    set((state) => ({
      cncStations: state.cncStations.map((st) =>
        st.id === stationId
          ? { ...st, status: 'CALLING', callingModel: modelName }
          : st
      ),
    }));

    showToast(`Đã điều AMR chở [${modelName}] tới [${stationId}]`, 'kuka');

    // Giả lập AMR cập bến sau 3 giây
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

  fastArriveCnc: (stationId) => {
    const station = get().cncStations.find((s) => s.id === stationId);
    if (!station) return;
    const modelName = station.callingModel || 'Model 1: Trục Rotor';
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
    get().showToast(`AMR đã cập bến [${stationId}] thành công!`, 'success');
  },

  // 3. Cập nhật Level CNC (Cố định bằng đúng Level được chỉ định của máy)
  updateCncStageLevel: (stationId) => {
    const station = get().cncStations.find((s) => s.id === stationId);
    if (!station || !station.currentRack) return;

    const targetLevel = station.assignedStageLevel; // CẬP NHẬT BẰNG ĐÚNG LEVEL ĐƯỢC CHỈ ĐỊNH
    const isFinalStage = targetLevel >= 3;

    if (isFinalStage) {
      const finishedRack = {
        ...station.currentRack,
        level: targetLevel,
      };

      // Giải phóng trạm CNC
      set((state) => ({
        cncStations: state.cncStations.map((st) =>
          st.id === stationId ? { ...st, status: 'EMPTY', currentRack: null } : st
        ),
      }));

      // Chuyển sang khu tẩy rửa
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

      get().showToast(
        `Hoàn tất Level ${targetLevel} tại [${stationId}] -> AMR đã chở sang [${slotAssigned || 'Khu Tẩy Rửa'}]!`,
        'kuka'
      );
    } else {
      const finishedRack = {
        ...station.currentRack,
        level: targetLevel,
      };

      // Giải phóng trạm để sẵn sàng nhận phôi tiếp theo, xe sẵn sàng cho máy công đoạn sau gọi
      set((state) => ({
        cncStations: state.cncStations.map((st) =>
          st.id === stationId ? { ...st, status: 'EMPTY', currentRack: null } : st
        ),
      }));

      get().showToast(
        `Đã hoàn tất Level ${targetLevel} (${station.stageName}) tại [${stationId}]! Xe [${finishedRack.rackId}] sẵn sàng cho Level ${targetLevel + 1}.`,
        'success'
      );
    }
  },

  // 4. Khu Tẩy Rửa: Giải phóng slot
  releaseWashingSlot: (slotId) => {
    set((state) => ({
      washingSlots: state.washingSlots.map((s) =>
        s.id === slotId ? { ...s, status: 'EMPTY', currentRack: null } : s
      ),
    }));
    get().showToast(`Đã giải phóng Slot ${slotId} về TRỐNG!`, 'success');
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
