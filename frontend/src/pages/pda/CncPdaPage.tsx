import React from 'react';
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

  const activeCount = cncStations.filter((s) => s.status !== 'EMPTY').length;

  return (
    <PdaLayoutWrapper
      title="PDA Vận Hành Trạm CNC"
      badge={`${activeCount}/${cncStations.length} Trạm Hoạt Động`}
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
