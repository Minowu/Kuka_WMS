import React, { useEffect } from 'react';
import { PdaLayoutWrapper } from '@/components/pda/PdaLayoutWrapper';
import { RawMaterialWizard } from '@/components/pda/RawMaterialWizard';
import { usePdaStore } from '@/store/usePdaStore';

export const RawMaterialPdaPage: React.FC = () => {
  const positions = usePdaStore((s) => s.positions);
  const models = usePdaStore((s) => s.models);
  const supplyRawMaterial = usePdaStore((s) => s.supplyRawMaterial);
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
      title="KHU NGUYÊN LIỆU"
      stationSubtitle="Vị Trí Cấp Phôi Sản Xuất"
    >
      <RawMaterialWizard
        positions={positions}
        models={models}
        onSupplyConfirm={supplyRawMaterial}
        showToast={showToast}
      />
    </PdaLayoutWrapper>
  );
};

export default RawMaterialPdaPage;
