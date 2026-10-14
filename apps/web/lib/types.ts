export type DashboardSummary = {
  connected_sources: number;
  tabs_scanned: number;
  timetable_entries: number;
  content_items: number;
  videos: number;
  pdfs: number;
  changes_today: number;
  sync_errors: number;
  last_successful_sync: string | null;
};

export type TimetableEntry = {
  id: string;
  source_id: string;
  class_date: string | null;
  day: string | null;
  start_time: string | null;
  end_time: string | null;
  stream: string | null;
  class_name: string | null;
  batch: string | null;
  subject: string | null;
  topic: string | null;
  teacher: string | null;
  confidence: number;
  warnings: string[];
  workbook_name: string;
  sheet_name: string;
  source_row: number;
  source_coordinates: string[];
};

export type ContentItem = {
  id: string;
  source_id: string;
  workbook_name: string;
  title: string;
  url: string;
  content_type: string;
  stream: string | null;
  class_name: string | null;
  batch: string | null;
  subject: string | null;
  topic: string | null;
  teacher: string | null;
  search_text?: string | null;
  sheet_name: string;
  source_row: number;
  coordinate: string;
  confidence: number;
  warnings: string[];
  record_kind?: string | null;
  status?: string | null;
  test_number?: string | null;
  test_date?: string | null;
  result_dashboard?: string | null;
  video_solution_update?: string | null;
  questions?: string | null;
  duration?: string | null;
  marks?: string | null;
  remarks?: string | null;
};

export type TestRecord = {
  id: string;
  source_id: string;
  workbook_name: string;
  sheet_name: string;
  source_row: number;
  created_date: string | null;
  course: string | null;
  class_name: string | null;
  board: string | null;
  subject: string | null;
  chapter_number: string | null;
  topic: string | null;
  made_by: string | null;
  questions: string | null;
  duration: string | null;
  marks: string | null;
  document_title: string | null;
  document_url: string | null;
  pdf_title: string | null;
  pdf_url: string | null;
  app_status: string | null;
  test_date_status: string | null;
  result_dashboard: string | null;
  video_solution_update: string | null;
  remarks: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
};

export type TestStatusBucket = {
  label: string;
  total: number;
  done: number;
  pending: number;
  not_due: number;
};


export type TestCycleSummary = {
  window_start: string;
  window_end: string;
  sunday_date: string;
  result_deadline: string;
  video_deadline: string;
  window_open: boolean;
  total_tests: number;
  app_done: number;
  app_pending: number;
  subject_counts: Record<string, number>;
  class_counts: Record<string, number>;
  course_counts: Record<string, number>;
};

export type TestMonitorResponse = {
  summary: {
    total_tests: number;
    new_tests_7days: number;
    app_status: TestStatusBucket;
    result_dashboard: TestStatusBucket;
    video_solution: TestStatusBucket;
    sheet_counts: Record<string, number>;
    subject_counts: Record<string, number>;
    class_counts: Record<string, number>;
    course_counts: Record<string, number>;
    tests_with_clickable_files: number;
    tests_without_clickable_files: number;
    scheduled_tests: number;
    data_quality: {
      total: number;
      missing_course: number;
      missing_class: number;
      missing_subject: number;
      missing_topic: number;
      missing_file_name: number;
      missing_clickable_link: number;
      missing_app_status: number;
      missing_test_date: number;
      missing_result_dashboard: number;
      missing_video_solution: number;
    };
    generated_at: string;
  };
  cycle: TestCycleSummary;
  upcoming_sunday_tests: TestRecord[];
  pending_app: TestRecord[];
  pending_result: TestRecord[];
  pending_video: TestRecord[];
  recent_tests: TestRecord[];
};

export type ChangeRecord = {
  id: string;
  source_id: string;
  workbook_name: string;
  sheet_name: string;
  coordinate: string;
  change_type: "added" | "updated" | "deleted";
  old_value: string | null;
  new_value: string | null;
  detected_at: string;
  category?: string | null;
  summary?: string | null;
  impact?: string | null;
  plain_location?: string | null;
  field_name?: string | null;
  row_label?: string | null;
  details?: Array<{
    field_name: string;
    change_type: "added" | "updated" | "deleted";
    old_value: string | null;
    new_value: string | null;
    coordinate?: string | null;
    row_number?: number | null;
  }>;
  affected_rows?: number[];
  affected_count?: number;
  group_kind?: "row" | "field" | "cell" | null;
};

export type ChangeSummary = {
  added: number;
  updated: number;
  deleted: number;
  total: number;
  sources_checked: number;
};

export type Paginated<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  search_ms?: number | null;
  normalized_query?: string | null;
};

export type SheetSource = {
  id: string;
  name: string;
  url: string;
  spreadsheet_id: string;
  enabled: boolean;
  created_at: string;
  last_sync_at: string | null;
  last_sync_status: string;
  last_error: string | null;
};

export type TabProfile = {
  name: string;
  kind: "timetable" | "weekly_planner" | "content_library" | "mixed" | "unknown";
  hidden: boolean;
  max_row: number;
  max_column: number;
  non_empty_cells: number;
  merged_ranges: string[];
  header_candidates: number[];
  detected_keywords: string[];
  link_count: number;
  date_count: number;
  time_count: number;
  confidence: number;
  warnings: string[];
  header_row: number | null;
  detected_columns: Record<string, string>;
  searchable_fields: string[];
  missing_recommended_fields: string[];
  search_ready: boolean;
  record_count: number;
};

export type WorkbookProfile = {
  source_id: string;
  workbook_name: string;
  analyzed_at: string;
  tabs: TabProfile[];
  total_non_empty_cells: number;
  total_links: number;
  warnings: string[];
};

export type SourceAnalysisSummary = {
  source: SheetSource;
  profile: WorkbookProfile | null;
  timetable_count: number;
  content_count: number;
  test_count: number;
  search_ready_tabs: number;
  needs_setup_tabs: number;
  tab_content_counts: Record<string, number>;
};

export type NotificationRule = {
  id: string;
  name: string;
  enabled: boolean;
  event_type: string;
  send_time: string | null;
  weekday: number | null;
  minutes_before: number | null;
  timezone: string;
  channels: string[];
  recipients: string[];
  streams: string[];
  classes: string[];
  subjects: string[];
  source_ids: string[];
  sheet_names: string[];
  include_pdf: boolean;
  include_excel: boolean;
  created_at: string;
};

export type NotificationDelivery = {
  id: string;
  rule_id: string;
  rule_name: string;
  channel: string;
  recipient: string;
  status: string;
  message: string;
  error: string | null;
  attempted_at: string;
  scheduled_for: string | null;
  is_test: boolean;
  dedupe_key: string;
};

export type NotificationStatus = {
  scheduler_active: boolean;
  scheduler_interval_seconds: number;
  sheet_refresh_minutes: number;
  page_refresh_minutes: number;
  configured_channels: Record<string, boolean>;
};

export type NotificationTestResponse = {
  rule_id: string;
  scheduler_ok: boolean;
  preview: string;
  deliveries: NotificationDelivery[];
};
