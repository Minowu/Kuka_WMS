import React, { useEffect } from 'react';
import { PdaLayoutWrapper } from '@/components/pda/PdaLayoutWrapper';
import { CncLineModal } from '@/components/pda/CncLineModal';
import { usePdaStore } from '@/store/usePdaStore';

export const CncPdaPage: React.FC = () => {
  const cncStations = usePdaStore((s) => s.cncStations);
  const models = usePdaStore((s) => s.models);
  const callMaterialToCnc = usePdaStore((s) => s.callMaterialToCnc);
  const updateCncStageLevel = usePdaStore((s) => s.updateCncStageLevel);
  const fastArriveCnc = usePdaStore((s) => s.fastArriveCnc);
  const showToast = usePdaStore((s) => s.showToast);
  const fetchFloorState = usePdaStore((s) => s.fetchFloorState);

  useEffect(() => {
    fetchFloorState();
    const interval = setInterval(() => {
      fetchFloorState();
    }, 4000);
    return () => clearInterval(interval);
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
        onFastArrive={fastArriveCnc}
        showToast={showToast}
      />
    </PdaLayoutWrapper>
  );
};

export default CncPdaPage;
