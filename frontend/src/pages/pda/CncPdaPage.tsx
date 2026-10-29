import React, { useEffect } from 'react';
import { PdaLayoutWrapper } from '@/components/pda/PdaLayoutWrapper';
import { CncLineModal } from '@/components/pda/CncLineModal';
import { usePdaStore } from '@/store/usePdaStore';

export const CncPdaPage: React.FC = () => {
  const cncStations = usePdaStore((s) => s.cncStations);
  const models = usePdaStore((s) => s.models);
  const callMaterialToCnc = usePdaStore((s) => s.callMaterialToCnc);
  const updateCncStageLevel = usePdaStore((s) => s.updateCncStageLevel);
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
      title="DÂY CHUYỀN CNC"
      stationSubtitle="Quản Lý Trạm Máy Gia Công"
    >
      <CncLineModal
        stations={cncStations}
        models={models}
        onCallMaterial={callMaterialToCnc}
        onUpdateLevel={updateCncStageLevel}
        showToast={showToast}
      />
    </PdaLayoutWrapper>
  );
};

export default CncPdaPage;
