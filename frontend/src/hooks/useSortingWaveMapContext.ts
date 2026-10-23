/**
 * Hook dùng chung cho map chia chọn theo wave — overview + detail.
 */
import { useMemo, useState } from "react";
import { message } from "@/components/ui";
import {
  useIncompleteVehicles,
  useSortingStationFills,
} from "@/hooks/useOutbound";
import { getSortingStationAssignmentApi } from "@/api/outbound";
import type { SortingStationAssignment } from "@/types/outbound";
import type { SortingWave } from "@/types/sortingWave";
import { useLocationByCodeMap } from "@/hooks/useWarehouseLocation";
import {
  buildStationOverlayLabels,
  enrichAssignmentLabels,
  ensureSortingStationLabels,
  mergeStationOverlayLabels,
} from "@/utils/sortingStationOverlay";
import {
  applyConfirmedPicksToOverlayLabels,
  EMPTY_STATION_PICK_CONFIRM,
  STATION_PICK_TOTAL_KEY,
  type StationPickConfirm,
} from "@/utils/sortingStationPickRows";

export function useSortingWaveMapContext(
  warehouseId: number,
  wave: SortingWave | null,
) {
  const sortingStationIds = useMemo(
    () => wave?.sorting_stations ?? [],
    [wave],
  );
  const outboundStationIds = useMemo(
    () => wave?.outbound_stations ?? [],
    [wave],
  );
  const waveStationIds = useMemo(() => {
    const merged = [...sortingStationIds, ...outboundStationIds];
    return [...new Set(merged)];
  }, [sortingStationIds, outboundStationIds]);
  const sortingStationIdSet = useMemo(
    () => new Set(sortingStationIds),
    [sortingStationIds],
  );
  const outboundStationIdSet = useMemo(
    () => new Set(outboundStationIds),
    [outboundStationIds],
  );

  const { data: incompleteVehiclesData } = useIncompleteVehicles(warehouseId);
  const incompleteVehicles = incompleteVehiclesData?.vehicles ?? [];
  const { locationByCode } = useLocationByCodeMap(warehouseId);
  const { data: sortingFillsData } = useSortingStationFills(
    warehouseId,
    wave?.id ?? null,
  );
  const fillStations = sortingFillsData?.stations ?? [];


  const mergedFillStations = fillStations;

  const [confirmedPicksByStation, setConfirmedPicksByStation] = useState<
    Record<string, StationPickConfirm>
  >({});

  const sortingStationCodes = useMemo(
    () =>
      sortingStationIds
        .map((id) => {
          const loc = Object.values(locationByCode).find(
            (item) => item.id === id,
          );
          return (loc?.location_code || "").trim();
        })
        .filter(Boolean),
    [sortingStationIds, locationByCode],
  );

  const stationOverlayLabels = useMemo(() => {
    const base = mergeStationOverlayLabels(
      {
        ...buildStationOverlayLabels(incompleteVehicles, locationByCode),
        ...enrichAssignmentLabels(
          sortingFillsData?.assignment_labels,
          locationByCode,
        ),
      },
      mergedFillStations,
      locationByCode,
    );
    const withSortingFallback = ensureSortingStationLabels(
      base,
      sortingStationCodes,
      locationByCode,
    );
    return applyConfirmedPicksToOverlayLabels(
      withSortingFallback,
      mergedFillStations,
      confirmedPicksByStation,
      locationByCode,
    );
  }, [
    incompleteVehicles,
    mergedFillStations,
    sortingFillsData?.assignment_labels,
    confirmedPicksByStation,
    locationByCode,
    sortingStationCodes,
  ]);

  const [stationAssignment, setStationAssignment] =
    useState<SortingStationAssignment | null>(null);
  const [selectedStationCode, setSelectedStationCode] = useState<string | null>(
    null,
  );
  const [selectedStationLocationId, setSelectedStationLocationId] = useState<
    number | null
  >(null);
  const [selectedStationKind, setSelectedStationKind] = useState<
    "sorting" | "outbound" | null
  >(null);

  const resolveStationKind = (
    locationId: number,
    locationType?: string | null,
  ): "sorting" | "outbound" => {
    const type = (locationType || "").trim();
    if (type === "outbound_station") return "outbound";
    if (
      type === "sorting_station" ||
      type === "breaking_pallet" ||
      type === "sorting"
    ) {
      return "sorting";
    }
    if (outboundStationIdSet.has(locationId)) return "outbound";
    if (sortingStationIdSet.has(locationId)) return "sorting";
    return "sorting";
  };

  const handleStationCellClick = async (payload: { locationCode: string }) => {
    const location = locationByCode[payload.locationCode];
    if (!location) {
      message.error(
        `Không tìm thấy warehouse location cho mã ${payload.locationCode}`,
      );
      return null;
    }

    const kind = resolveStationKind(location.id, location.location_type);
    setSelectedStationCode(payload.locationCode);
    setSelectedStationLocationId(location.id);
    setSelectedStationKind(kind);

    if (kind === "outbound") {
      setStationAssignment(null);
      return { kind: "outbound" as const, location, assignment: null };
    }

    try {
      const assignment = await getSortingStationAssignmentApi({
        warehouseId,
        locationCode: payload.locationCode,
        locationId: location.id,
      });
      setStationAssignment(assignment);
      if (assignment.is_assigned || assignment.has_fill) {
        return {
          kind: "sorting" as const,
          location,
          assignment,
          mode: "pick" as const,
        };
      }
      return {
        kind: "sorting" as const,
        location,
        assignment,
        mode: "assign" as const,
      };
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Không kiểm tra được trạng thái gán ô";
      message.error(detail);
      return null;
    }
  };

  const clearStationSelection = () => {
    setStationAssignment(null);
    setSelectedStationCode(null);
    setSelectedStationLocationId(null);
    setSelectedStationKind(null);
  };

  const selectedFillStation = useMemo(
    () =>
      selectedStationCode
        ? (mergedFillStations.find(
            (station) => station.location_code === selectedStationCode,
          ) ?? null)
        : null,
    [mergedFillStations, selectedStationCode],
  );

  const selectedPreviousPicks = useMemo(
    () =>
      selectedStationCode
        ? (confirmedPicksByStation[selectedStationCode] ??
          EMPTY_STATION_PICK_CONFIRM)
        : EMPTY_STATION_PICK_CONFIRM,
    [confirmedPicksByStation, selectedStationCode],
  );

  const handlePickConfirm = (
    locationCode: string,
    picks: StationPickConfirm,
  ) => {
    setConfirmedPicksByStation((prev) => {
      const prevPicks = prev[locationCode] ?? {};
      const merged: StationPickConfirm = { ...prevPicks };
      const qty =
        picks[STATION_PICK_TOTAL_KEY] ??
        Object.values(picks).reduce((sum, value) => sum + value, 0);
      if (qty > 0) {
        merged[STATION_PICK_TOTAL_KEY] =
          (merged[STATION_PICK_TOTAL_KEY] ?? 0) + qty;
      }
      return {
        ...prev,
        [locationCode]: merged,
      };
    });
  };

  return {
    waveStationIds,
    stationOverlayLabels,
    stationAssignment,
    selectedStationCode,
    selectedStationLocationId,
    selectedStationKind,
    selectedFillStation,
    selectedPreviousPicks,
    handleStationCellClick,
    clearStationSelection,
    handlePickConfirm,
    setStationAssignment,
  };
}
