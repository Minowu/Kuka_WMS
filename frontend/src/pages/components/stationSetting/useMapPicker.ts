import { useCallback, useState } from 'react';
import type { MapPickerOptions } from './stationSettingTypes';

type MapPickerState = MapPickerOptions & { open: boolean };

const CLOSED_PICKER: MapPickerState = { open: false, title: '', onSelect: () => {} };

export function useMapPicker() {
  const [mapPicker, setMapPicker] = useState<MapPickerState>(CLOSED_PICKER);

  const openMapPicker = useCallback((options: MapPickerOptions) => {
    setMapPicker({ open: true, ...options });
  }, []);

  const closeMapPicker = useCallback(() => {
    setMapPicker((prev) => ({ ...prev, open: false }));
  }, []);

  return { mapPicker, openMapPicker, closeMapPicker };
}
