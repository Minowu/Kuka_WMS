const POS_BADGE_CLASSES: Record<number, string> = {
  1: 'bg-blue-100 text-blue-700 border-blue-200',
  2: 'bg-purple-100 text-purple-700 border-purple-200',
  3: 'bg-amber-100 text-amber-700 border-amber-200',
  4: 'bg-emerald-100 text-emerald-700 border-emerald-200',
};

const DEFAULT_BADGE_CLASS = 'bg-slate-100 text-slate-600 border-slate-200';

const SIZE_CLASSES = {
  default: 'text-xs px-2',
  small: 'text-[10px] px-1.5',
};

interface PosBadgeProps {
  position?: number | null;
  size?: keyof typeof SIZE_CLASSES;
}

/** Nhãn vị trí đỗ P1..P4 của máy CNC. */
export default function PosBadge({ position, size = 'default' }: PosBadgeProps) {
  const colorClass = (position && POS_BADGE_CLASSES[position]) || DEFAULT_BADGE_CLASS;

  return (
    <span className={`font-mono font-bold py-0.5 rounded border ${SIZE_CLASSES[size]} ${colorClass}`}>
      P{position || '?'}
    </span>
  );
}
