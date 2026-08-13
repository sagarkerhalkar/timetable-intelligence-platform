"use client";

import { pageNumbers } from "../lib/pagination";

type Props = {
  page: number;
  pages: number;
  total: number;
  start: number;
  end: number;
  onPageChange: (page: number) => void;
  label?: string;
};

export function PaginationControls({ page, pages, total, start, end, onPageChange, label = "items" }: Props) {
  if (total <= 0) return null;
  const numbers = pageNumbers(page, pages, 2);
  return <nav className="app-pagination" aria-label={`${label} pages`}>
    <div className="app-pagination-summary"><strong>{start + 1}–{end}</strong><span>of {total.toLocaleString("en-IN")} {label}</span></div>
    <div className="app-pagination-buttons">
      <button type="button" disabled={page <= 1} onClick={() => onPageChange(1)} aria-label="First page">«</button>
      <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>← Previous</button>
      <div className="app-pagination-numbers">{numbers.map((number) => <button type="button" key={number} className={number === page ? "active" : ""} aria-current={number === page ? "page" : undefined} onClick={() => onPageChange(number)}>{number}</button>)}</div>
      <button type="button" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>Next →</button>
      <button type="button" disabled={page >= pages} onClick={() => onPageChange(pages)} aria-label="Last page">»</button>
    </div>
  </nav>;
}
