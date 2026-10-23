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
    const interval = setInterval(() => {
      fetchFloorState();
    }, 60000);
    return () => clearInterval(interval);
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
