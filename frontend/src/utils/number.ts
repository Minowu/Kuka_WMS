export function parsePositiveInteger(value: unknown): number | null {
  if (value == null || value === "") return null;
  const num = Number(String(value).replace(/,/g, "").trim());
  if (!Number.isFinite(num) || num <= 0) return null;

  const int = Math.round(num);
  if (Math.abs(num - int) > 1e-9) return null;

  return int;
}

export function parseNonNegativeInteger(value: unknown): number | null {
  if (value == null || value === "") return null;
  const num = Number(String(value).replace(/,/g, "").trim());
  if (!Number.isFinite(num) || num < 0) return null;

  const int = Math.round(num);
  if (Math.abs(num - int) > 1e-9) return null;

  return int;
}

export function toDisplayInteger(value: unknown): string {
  if (value == null || value === "") return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  return String(Math.trunc(num));
}

export function padTwoDigits(value: number): string {
  return String(value).padStart(2, "0");
}

export function toInteger(value: unknown, fallback = 0): number {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.trunc(num);
}
