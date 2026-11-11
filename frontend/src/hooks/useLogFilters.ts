import { useState } from 'react';
import { LOG_PAGE_SIZE } from '@/constants/auditLog';
import type { CommonLogParams } from '@/types/auditLog';

/** Filter + pagination state shared by the audit and action log tabs. */
export function useLogFilters<T extends CommonLogParams>() {
  const [filters, setFilters] = useState<T>({} as T);
  const [page, setPage] = useState(1);

  const setFilter = (key: keyof T, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({} as T);
    setPage(1);
  };

  const params: T = { ...filters, page, page_size: LOG_PAGE_SIZE };

  return { filters, params, page, setPage, setFilter, resetFilters };
}
