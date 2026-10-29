import React, { useEffect } from 'react';
import { PdaLayoutWrapper } from '@/components/pda/PdaLayoutWrapper';
import { WashingStationModal } from '@/components/pda/WashingStationModal';
import { usePdaStore } from '@/store/usePdaStore';

export const WashingPdaPage: React.FC = () => {
  const washingSlots = usePdaStore((s) => s.washingSlots);
  const releaseWashingSlot = usePdaStore((s) => s.releaseWashingSlot);
  const showToast = usePdaStore((s) => s.showToast);
  const fetchFloorState = usePdaStore((s) => s.fetchFloorState);

  useEffect(() => {
    fetchFloorState();

    let intervalId: number | null = null;

    const startInterval = () => {
      if (!intervalId) {
        intervalId = window.setInterval(() => {
          if (document.visibilityState === 'visible') {
            fetchFloorState();
          }
        }, 60000);
      }
    };

    const stopInterval = () => {
      if (intervalId) {
        window.clearInterval(intervalId);
        intervalId = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchFloorState();
        startInterval();
      } else {
        stopInterval();
      }
    };

    startInterval();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      stopInterval();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [fetchFloorState]);

  return (
    <PdaLayoutWrapper
      title="KHU TẨY RỬA"
      stationSubtitle="4 Slot Tiếp Nhận Phôi Hoàn Thiện"
    >
      <WashingStationModal
        slots={washingSlots}
        onReleaseSlot={releaseWashingSlot}
        showToast={showToast}
      />
    </PdaLayoutWrapper>
  );
};

export default WashingPdaPage;
