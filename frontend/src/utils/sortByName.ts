export function compareNatural(a?: string | null, b?: string | null): number {
  return (a ?? '').localeCompare(b ?? '', 'vi', { numeric: true });
}

export function sortByName<T extends { name: string }>(list: T[]): T[] {
  return [...list].sort((a, b) => compareNatural(a.name, b.name));
}
