import React, { useEffect, useMemo, useRef, useState } from "react";
import { Modal, Button, Alert, Select, message } from "@/components/ui";
import {
  useImportWarehouseMap,
  usePreviewWarehouseMapImport,
} from "@/hooks/useWarehouseMap";
import type {
  MapRemapEntry,
  MapSyncRetiredItem,
  WarehouseMapImportResult,
} from "@/types/warehouseMap";

interface WarehouseMapImportDialogProps {
  open: boolean;
  onClose: () => void;
  warehouseId: number;
}

function extractErrorDetail(error: unknown): string {
  const err = error as { response?: { data?: { detail?: unknown } } };
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e: { msg?: string; loc?: string[] }) => {
        const field = e.loc?.slice(-1)[0] ?? "";
        return field ? `${field}: ${e.msg}` : (e.msg ?? "");
      })
      .filter(Boolean)
      .join("; ");
  }
  return "Không thể import warehouse map. Vui lòng thử lại.";
}

const binLabel = (item: MapSyncRetiredItem) =>
  item.bin_code || item.location_name || String(item.location_id);

const totalReferences = (item: MapSyncRetiredItem) =>
  Object.values(item.references).reduce((sum, n) => sum + n, 0);

const referenceSummary = (item: MapSyncRetiredItem) =>
  Object.entries(item.references)
    .map(([table, count]) => `${table}: ${count}`)
    .join(", ");

const WarehouseMapImportDialog: React.FC<WarehouseMapImportDialogProps> = ({
  open,
  onClose,
  warehouseId,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [preview, setPreview] = useState<WarehouseMapImportResult | null>(null);
  const [remapDraft, setRemapDraft] = useState<Record<string, string>>({});

  const previewMutation = usePreviewWarehouseMapImport();
  const importMutation = useImportWarehouseMap();
  const isPending = previewMutation.isPending || importMutation.isPending;

  const resetForm = () => {
    setSelectedFile(null);
    setErrorMsg(null);
    setPreview(null);
    setRemapDraft({});
    if (fileInputRef.current) fileInputRef.current.value = "";
    previewMutation.reset();
    importMutation.reset();
  };

  useEffect(() => {
    if (!open) return;
    resetForm();
    // resetForm only touches local state and the two mutations' reset helpers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  /** Bins that exist in the new map — the only valid remap targets. */
  const targetBinOptions = useMemo(() => {
    if (!preview) return [];
    const bins = [
      ...preview.matched.map((m) => m.bin_code),
      ...preview.created.map((c) => c.bin_code),
    ].filter((bin): bin is string => !!bin);
    return [...new Set(bins)]
      .sort((a, b) => a.localeCompare(b))
      .map((bin) => ({ value: bin, label: bin }));
  }, [preview]);

  /** Locations leaving the map that still have rows pointing at them. */
  const needsAttention = useMemo(() => {
    if (!preview) return [];
    return [
      ...preview.blocked,
      ...preview.retired.filter((item) => totalReferences(item) > 0),
    ];
  }, [preview]);

  const remapEntries = useMemo<MapRemapEntry[]>(
    () =>
      Object.entries(remapDraft)
        .filter(([, toBin]) => !!toBin)
        .map(([fromBin, toBin]) => ({ from_bin: fromBin, to_bin: toBin })),
    [remapDraft],
  );

  const unresolvedBlocked = useMemo(
    () => (preview?.blocked ?? []).filter((item) => !remapDraft[binLabel(item)]),
    [preview, remapDraft],
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setPreview(null);
    setRemapDraft({});
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const fileName = file.name.toLowerCase();
    const isZip = fileName.endsWith(".zip");
    const isJson = fileName.endsWith(".json");

    if (!isZip && !isJson) {
      message.error("Chỉ hỗ trợ file bản đồ ZIP (.zip) hoặc JSON KUKA SLAM (.json)");
      e.target.value = "";
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      message.error("File bản đồ trống, vui lòng chọn file khác");
      e.target.value = "";
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setErrorMsg(null);
  };

  const runPreview = () => {
    if (!selectedFile) {
      message.warning("Vui lòng chọn file bản đồ trước khi kiểm tra");
      return;
    }
    if (warehouseId <= 0) {
      message.error("Vui lòng chọn kho trước khi import");
      return;
    }

    setErrorMsg(null);
    previewMutation.mutate(
      { warehouseId, file: selectedFile, remap: remapEntries },
      {
        onSuccess: (result) => setPreview(result),
        onError: (error) => setErrorMsg(extractErrorDetail(error)),
      },
    );
  };

  const runImport = () => {
    if (!selectedFile) return;

    setErrorMsg(null);
    importMutation.mutate(
      { warehouseId, file: selectedFile, remap: remapEntries },
      {
        onSuccess: (result) => {
          message.success(
            `Import thành công: giữ ${result.counts.matched} vị trí, ` +
              `thêm ${result.counts.created}, dời tham chiếu ${result.counts.remapped}, ` +
              `ngưng dùng ${result.counts.retired}.`,
          );
          resetForm();
          onClose();
        },
        onError: (error) => setErrorMsg(extractErrorDetail(error)),
      },
    );
  };

  const handleClose = () => {
    if (isPending) return;
    resetForm();
    onClose();
  };

  return (
    <Modal
      title="Import Warehouse Map"
      open={open}
      onCancel={handleClose}
      mask={{ closable: !isPending }}
      closable={!isPending}
      width={preview ? 780 : undefined}
      footer={
        <div className="flex justify-end gap-2 pt-2">
          <Button
            variant="secondary"
            onClick={handleClose}
            disabled={isPending}
          >
            Hủy
          </Button>
          <Button
            variant="secondary"
            onClick={runPreview}
            loading={previewMutation.isPending}
            disabled={!selectedFile || isPending}
          >
            {preview ? "Kiểm tra lại" : "Kiểm tra thay đổi"}
          </Button>
          <Button
            variant="primary"
            onClick={runImport}
            loading={importMutation.isPending}
            disabled={!preview || unresolvedBlocked.length > 0 || isPending}
          >
            Import
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Chọn file bản đồ (.zip hoặc .json KUKA SLAM)
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.json,application/zip,application/json"
            onChange={handleFileSelect}
            disabled={isPending}
            className="
              block w-full text-sm text-slate-500
              file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0
              file:text-sm file:font-semibold file:bg-brand-primary/10 file:text-brand-primary
              hover:file:bg-brand-primary/20 file:cursor-pointer file:transition-colors
              disabled:opacity-50
            "
          />
          {selectedFile && (
            <p className="mt-2 text-xs text-slate-500">
              {selectedFile.name}{" "}
              <span className="text-slate-400">
                ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </p>
          )}
        </div>

        {errorMsg && <Alert variant="error">{errorMsg}</Alert>}

        {preview && (
          <div className="space-y-4">
            <div className="grid grid-cols-5 gap-2 text-center">
              {[
                { label: "Giữ nguyên", value: preview.counts.matched },
                { label: "Thêm mới", value: preview.counts.created },
                { label: "Dời tham chiếu", value: preview.counts.remapped },
                { label: "Ngưng dùng", value: preview.counts.retired },
                { label: "Đang chặn", value: preview.counts.blocked },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-lg bg-slate-50 px-2 py-3"
                >
                  <div className="text-lg font-semibold text-slate-700">
                    {item.value}
                  </div>
                  <div className="text-xs text-slate-500">{item.label}</div>
                </div>
              ))}
            </div>

            <p className="text-xs text-slate-500">
              Map có {preview.total_shelves} vị trí. Các vị trí khớp theo mã bin
              giữ nguyên ID nên toàn bộ tồn kho và lịch sử không bị ảnh hưởng.
            </p>

            {unresolvedBlocked.length > 0 && (
              <Alert variant="error">
                {unresolvedBlocked.length} vị trí còn tồn kho nhưng không còn
                trong map mới. Hãy chọn bin đích để dời tồn sang trước khi
                import.
              </Alert>
            )}

            {needsAttention.length > 0 && (
              <div>
                <div className="mb-2 text-sm font-medium text-slate-700">
                  Vị trí rời khỏi map nhưng vẫn còn dữ liệu tham chiếu
                </div>
                <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                  {needsAttention.map((item) => {
                    const label = binLabel(item);
                    const isBlocked = !!item.quantity;
                    return (
                      <div
                        key={item.location_id}
                        className={`rounded-lg border px-3 py-2 ${
                          isBlocked
                            ? "border-red-200 bg-red-50"
                            : "border-slate-200 bg-white"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium text-slate-700">
                              {label}
                              {isBlocked && (
                                <span className="ml-2 text-xs font-normal text-red-600">
                                  còn tồn {item.quantity}
                                </span>
                              )}
                            </div>
                            <div className="truncate text-xs text-slate-400">
                              {referenceSummary(item) || "không còn tham chiếu"}
                            </div>
                          </div>
                          <div className="w-52 shrink-0">
                            <Select
                              showSearch
                              allowClear
                              size="small"
                              placeholder="Dời sang bin..."
                              options={targetBinOptions}
                              value={remapDraft[label] ?? undefined}
                              disabled={isPending}
                              optionFilterProp="label"
                              onChange={(value) =>
                                setRemapDraft((prev) => {
                                  const next = { ...prev };
                                  if (value) next[label] = value as string;
                                  else delete next[label];
                                  return next;
                                })
                              }
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  Bỏ trống nếu muốn giữ lịch sử ở vị trí cũ. Vị trí đó sẽ được
                  đánh dấu ngưng sử dụng thay vì bị xoá.
                </p>
              </div>
            )}

            {preview.nodes_without_bin_code.length > 0 && (
              <Alert variant="info">
                {preview.nodes_without_bin_code.length} node trong map chưa được
                đặt tên theo dạng{" "}
                <code className="rounded bg-black/5 px-1">
                  R1_C13_L1_BKH1.13
                </code>
                , nên sẽ được tạo mới ở mỗi lần import. Nên đặt tên node trong
                map editor để giữ được lịch sử.
              </Alert>
            )}
          </div>
        )}

        {!preview && (
          <p className="text-xs text-slate-400">
            ZIP phải chứa file{" "}
            <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-500">
              compress.json
            </code>
            . Bấm <b>Kiểm tra thay đổi</b> để xem trước; không có gì bị ghi cho
            đến khi bạn bấm Import.
          </p>
        )}
      </div>
    </Modal>
  );
};

export default WarehouseMapImportDialog;
