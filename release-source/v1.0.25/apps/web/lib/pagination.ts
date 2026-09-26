export type PageSlice<T> = {
  items: T[];
  page: number;
  pages: number;
  pageSize: number;
  total: number;
  start: number;
  end: number;
};

export function pageCount(total: number, pageSize: number): number {
  const safeSize = Math.max(1, Math.floor(pageSize));
  return Math.max(1, Math.ceil(Math.max(0, total) / safeSize));
}

export function clampPage(page: number, total: number, pageSize: number): number {
  return Math.min(Math.max(1, Math.floor(page) || 1), pageCount(total, pageSize));
}

export function paginateItems<T>(items: readonly T[], page: number, pageSize: number): PageSlice<T> {
  const safeSize = Math.max(1, Math.floor(pageSize));
  const safePage = clampPage(page, items.length, safeSize);
  const start = (safePage - 1) * safeSize;
  const pageItems = items.slice(start, start + safeSize);
  return {
    items: pageItems,
    page: safePage,
    pages: pageCount(items.length, safeSize),
    pageSize: safeSize,
    total: items.length,
    start,
    end: start + pageItems.length,
  };
}

export function pageNumbers(page: number, pages: number, radius = 2): number[] {
  const safePages = Math.max(1, Math.floor(pages));
  const safePage = Math.min(Math.max(1, Math.floor(page) || 1), safePages);
  const safeRadius = Math.max(0, Math.floor(radius));
  const start = Math.max(1, safePage - safeRadius);
  const end = Math.min(safePages, safePage + safeRadius);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}
