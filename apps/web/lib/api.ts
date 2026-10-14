export type { SheetSource } from "./types";
import type {
  ChangeRecord,
  ChangeSummary,
  ContentItem,
  DashboardSummary,
  NotificationDelivery,
  NotificationRule,
  NotificationStatus,
  Paginated,
  SheetSource,
  SourceAnalysisSummary,
  TestMonitorResponse,
  TimetableEntry
} from "./types";

export const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const API_URL = process.env.INTERNAL_API_URL ?? PUBLIC_API_URL;

type JsonFetchOptions = Readonly<{
  revalidate?: number;
  timeoutMs?: number;
}>;

async function getJson<T>(path: string, fallback: T, options: JsonFetchOptions = {}): Promise<T> {
  const revalidate = options.revalidate ?? 15;
  const timeoutMs = options.timeoutMs ?? 5000;
  try {
    const response = await fetch(`${API_URL}${path}`, revalidate > 0
      ? {
          next: { revalidate },
          signal: AbortSignal.timeout(timeoutMs)
        }
      : {
          cache: "no-store",
          signal: AbortSignal.timeout(timeoutMs)
        }
    );
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

function queryString(params: Record<string, string | number | boolean | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  return search.toString();
}

export const demoDashboard: DashboardSummary = {
  connected_sources: 0,
  tabs_scanned: 0,
  timetable_entries: 0,
  content_items: 0,
  videos: 0,
  pdfs: 0,
  changes_today: 0,
  sync_errors: 0,
  last_successful_sync: null
};

export async function getDashboard(): Promise<DashboardSummary> {
  return getJson("/api/v1/dashboard", demoDashboard, { revalidate: 15, timeoutMs: 4000 });
}

export async function getTimetable(params: {
  page?: number;
  pageSize?: number;
  classDate?: string;
  dateFrom?: string;
  dateTo?: string;
  stream?: string;
  className?: string;
  subject?: string;
  latest?: boolean;
  upcoming?: boolean;
} = {}): Promise<Paginated<TimetableEntry>> {
  const query = queryString({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 25,
    class_date: params.classDate,
    date_from: params.dateFrom,
    date_to: params.dateTo,
    stream: params.stream,
    class_name: params.className,
    subject: params.subject,
    latest: params.latest ?? false,
    upcoming: params.upcoming ?? false
  });
  return getJson(`/api/v1/timetable?${query}`, {
    items: [], page: 1, page_size: params.pageSize ?? 25, total: 0, pages: 1
  });
}

export async function getContent(params: {
  page?: number;
  pageSize?: number;
  query?: string;
  contentType?: string;
  stream?: string;
  className?: string;
  subject?: string;
  sourceId?: string;
  sheetName?: string;
} = {}): Promise<Paginated<ContentItem>> {
  const query = queryString({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 24,
    query: params.query,
    content_type: params.contentType,
    stream: params.stream,
    class_name: params.className,
    subject: params.subject,
    source_id: params.sourceId,
    sheet_name: params.sheetName
  });
  return getJson(`/api/v1/content?${query}`, {
    items: [], page: 1, page_size: params.pageSize ?? 24, total: 0, pages: 1
  });
}

export async function getChanges(params: {
  page?: number;
  pageSize?: number;
  sourceId?: string;
  sheetName?: string;
  changeType?: string;
  period?: string;
  view?: string;
} = {}): Promise<Paginated<ChangeRecord>> {
  const query = queryString({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 25,
    source_id: params.sourceId,
    sheet_name: params.sheetName,
    change_type: params.changeType,
    period: params.period ?? "today",
    view: params.view ?? "cells"
  });
  return getJson(`/api/v1/changes?${query}`, {
    items: [], page: 1, page_size: params.pageSize ?? 25, total: 0, pages: 1
  });
}

export async function getChangeSummary(params: {
  sourceId?: string;
  sheetName?: string;
  period?: string;
} = {}): Promise<ChangeSummary> {
  const query = queryString({
    source_id: params.sourceId,
    sheet_name: params.sheetName,
    period: params.period ?? "today"
  });
  return getJson(`/api/v1/changes/summary?${query}`, {
    added: 0, updated: 0, deleted: 0, total: 0, sources_checked: 0
  });
}

export async function getSources(): Promise<SheetSource[]> {
  return getJson("/api/v1/sources", [], { revalidate: 30, timeoutMs: 4000 });
}

export async function getSourceAnalysis(): Promise<SourceAnalysisSummary[]> {
  return getJson("/api/v1/source-analysis", [], { revalidate: 30, timeoutMs: 5000 });
}

export async function getNotificationRules(): Promise<NotificationRule[]> {
  return getJson("/api/v1/notification-rules", [], { revalidate: 0, timeoutMs: 5000 });
}

export async function getNotificationStatus(): Promise<NotificationStatus> {
  return getJson("/api/v1/notification-status", {
    scheduler_active: false, scheduler_interval_seconds: 60, sheet_refresh_minutes: 30,
    page_refresh_minutes: 5, configured_channels: {}
  }, { revalidate: 0, timeoutMs: 5000 });
}

export async function getNotificationDeliveries(): Promise<NotificationDelivery[]> {
  return getJson("/api/v1/notification-deliveries?limit=30", [], { revalidate: 0, timeoutMs: 5000 });
}


export async function getTestTabCounts(sourceId?: string): Promise<Record<string, number>> {
  const query = queryString({ source_id: sourceId });
  return getJson(`/api/v1/test-monitor/tabs${query ? `?${query}` : ""}`, {}, { revalidate: 30, timeoutMs: 4000 });
}

export async function getTestMonitor(sourceId?: string, sheetName?: string, compact = true): Promise<TestMonitorResponse> {
  const query = queryString({ source_id: sourceId, sheet_name: sheetName, compact });
  return getJson(`/api/v1/test-monitor${query ? `?${query}` : ""}`, {
    summary: {
      total_tests: 0,
      new_tests_7days: 0,
      app_status: { label: "App Status", total: 0, done: 0, pending: 0, not_due: 0 },
      result_dashboard: { label: "Result Dashboard", total: 0, done: 0, pending: 0, not_due: 0 },
      video_solution: { label: "Video Solution", total: 0, done: 0, pending: 0, not_due: 0 },
      sheet_counts: {},
      subject_counts: {},
      class_counts: {},
      course_counts: {},
      tests_with_clickable_files: 0,
      tests_without_clickable_files: 0,
      scheduled_tests: 0,
      data_quality: {
        total: 0,
        missing_course: 0,
        missing_class: 0,
        missing_subject: 0,
        missing_topic: 0,
        missing_file_name: 0,
        missing_clickable_link: 0,
        missing_app_status: 0,
        missing_test_date: 0,
        missing_result_dashboard: 0,
        missing_video_solution: 0
      },
      generated_at: new Date(0).toISOString()
    },
    cycle: {
      window_start: new Date(0).toISOString(),
      window_end: new Date(0).toISOString(),
      sunday_date: "1970-01-04",
      result_deadline: new Date(0).toISOString(),
      video_deadline: new Date(0).toISOString(),
      window_open: false,
      total_tests: 0,
      app_done: 0,
      app_pending: 0,
      subject_counts: {},
      class_counts: {},
      course_counts: {}
    },
    upcoming_sunday_tests: [],
    pending_app: [],
    pending_result: [],
    pending_video: [],
    recent_tests: []
  }, { revalidate: 20, timeoutMs: 5000 });
}
