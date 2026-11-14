import type { ReactNode } from 'react';
import { InfoCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { Button } from '@/components/ui';
import type { BannerTheme } from './stationSettingTypes';

interface ZoneInfoBannerProps {
  theme: BannerTheme;
  title: string;
  children: ReactNode;
  buttonText: string;
  onAdd: () => void;
}

export default function ZoneInfoBanner({ theme, title, children, buttonText, onAdd }: ZoneInfoBannerProps) {
  return (
    <div className={`flex items-center justify-between border rounded-xl p-4 ${theme.bannerClass}`}>
      <div className="flex items-center gap-3">
        <InfoCircleOutlined className={`text-xl shrink-0 ${theme.iconClass}`} />
        <div className={`text-xs leading-relaxed ${theme.textClass}`}>
          <span className="font-bold">{title}</span> {children}
        </div>
      </div>
      <Button
        onClick={onAdd}
        icon={<PlusOutlined />}
        className={`!border-none !text-white !h-9 !px-4 !rounded-lg font-semibold shrink-0 ${theme.buttonClass}`}
      >
        {buttonText}
      </Button>
    </div>
  );
}
