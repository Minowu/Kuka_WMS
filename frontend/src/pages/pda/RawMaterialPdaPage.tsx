import React from 'react';
import { PdaLayoutWrapper } from '@/components/pda/PdaLayoutWrapper';
import { RawMaterialWizard } from '@/components/pda/RawMaterialWizard';
import { usePdaStore } from '@/store/usePdaStore';

export const RawMaterialPdaPage: React.FC = () => {
  const positions = usePdaStore((s) => s.positions);
  const models = usePdaStore((s) => s.models);
  const supplyRawMaterial = usePdaStore((s) => s.supplyRawMaterial);
  const showToast = usePdaStore((s) => s.showToast);

  return (
    <PdaLayoutWrapper
      title="KHU NGUYÊN LIỆU"
      stationSubtitle="7 Vị Trí Cấp Phôi"
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
