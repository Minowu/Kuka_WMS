import React from 'react';
import { PdaLayoutWrapper } from '@/components/pda/PdaLayoutWrapper';
import { WashingStationModal } from '@/components/pda/WashingStationModal';
import { usePdaStore } from '@/store/usePdaStore';

export const WashingPdaPage: React.FC = () => {
  const washingSlots = usePdaStore((s) => s.washingSlots);
  const releaseWashingSlot = usePdaStore((s) => s.releaseWashingSlot);
  const simulateArriveWashing = usePdaStore((s) => s.simulateArriveWashing);
  const showToast = usePdaStore((s) => s.showToast);

  const occupiedCount = washingSlots.filter((s) => s.status === 'OCCUPIED').length;

  return (
    <PdaLayoutWrapper
      title="PDA Khu Vực Tẩy Rửa"
      badge={`${occupiedCount}/4 Slot Có Hàng`}
    >
      <WashingStationModal
        slots={washingSlots}
        onReleaseSlot={releaseWashingSlot}
        onSimulateArrive={simulateArriveWashing}
        showToast={showToast}
      />
    </PdaLayoutWrapper>
  );
};

export default WashingPdaPage;
