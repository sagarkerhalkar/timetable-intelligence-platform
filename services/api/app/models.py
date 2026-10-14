from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class TabKind(StrEnum):
    TIMETABLE = "timetable"
    WEEKLY_PLANNER = "weekly_planner"
    CONTENT_LIBRARY = "content_library"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ContentType(StrEnum):
    VIDEO = "video"
    PDF = "pdf"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    FORM = "form"
    IMAGE = "image"
    EXTERNAL_LINK = "external_link"
    UNKNOWN = "unknown"


class ChangeType(StrEnum):
    ADDED = "added"
    UPDATED = "updated"
    DELETED = "deleted"


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: HttpUrl
    enabled: bool = True


class SheetSource(BaseModel):
    id: str
    name: str
    url: str
    spreadsheet_id: str
    enabled: bool
    created_at: datetime
    last_sync_at: datetime | None = None
    last_sync_status: str = "never"
    last_error: str | None = None


class CellSnapshot(BaseModel):
    source_id: str
    workbook_name: str
    sheet_name: str
    coordinate: str
    row: int
    column: int
    value: str
    formula: str | None = None
    hyperlink: str | None = None
    style_key: str = ""

    @property
    def stable_key(self) -> str:
        return f"{self.source_id}:{self.sheet_name}:{self.coordinate}"


class TabProfile(BaseModel):
    name: str
    kind: TabKind
    hidden: bool = False
    max_row: int
    max_column: int
    non_empty_cells: int
    merged_ranges: list[str]
    header_candidates: list[int]
    detected_keywords: list[str]
    link_count: int
    date_count: int
    time_count: int
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    header_row: int | None = None
    detected_columns: dict[str, str] = Field(default_factory=dict)
    searchable_fields: list[str] = Field(default_factory=list)
    missing_recommended_fields: list[str] = Field(default_factory=list)
    search_ready: bool = False
    record_count: int = 0


class WorkbookProfile(BaseModel):
    source_id: str
    workbook_name: str
    analyzed_at: datetime
    tabs: list[TabProfile]
    total_non_empty_cells: int
    total_links: int
    warnings: list[str] = Field(default_factory=list)


class SourceAnalysisSummary(BaseModel):
    source: SheetSource
    profile: WorkbookProfile | None = None
    timetable_count: int = 0
    content_count: int = 0
    test_count: int = 0
    search_ready_tabs: int = 0
    needs_setup_tabs: int = 0
    tab_content_counts: dict[str, int] = Field(default_factory=dict)


class TimetableEntry(BaseModel):
    id: str
    source_id: str
    workbook_name: str
    sheet_name: str
    source_row: int
    source_coordinates: list[str]
    class_date: date | None = None
    day: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    stream: str | None = None
    class_name: str | None = None
    batch: str | None = None
    subject: str | None = None
    topic: str | None = None
    teacher: str | None = None
    search_text: str | None = None
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    fingerprint: str


class ContentItem(BaseModel):
    id: str
    source_id: str
    workbook_name: str
    sheet_name: str
    coordinate: str
    source_row: int
    url: str
    title: str
    content_type: ContentType
    stream: str | None = None
    class_name: str | None = None
    batch: str | None = None
    subject: str | None = None
    topic: str | None = None
    teacher: str | None = None
    search_text: str | None = None
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    fingerprint: str
    record_kind: str | None = None
    status: str | None = None
    test_number: str | None = None
    test_date: str | None = None
    result_dashboard: str | None = None
    video_solution_update: str | None = None
    questions: str | None = None
    duration: str | None = None
    marks: str | None = None
    remarks: str | None = None


class TestRecord(BaseModel):
    id: str
    source_id: str
    workbook_name: str
    sheet_name: str
    source_row: int
    source_coordinates: list[str] = Field(default_factory=list)
    created_date: date | None = None
    course: str | None = None
    class_name: str | None = None
    board: str | None = None
    subject: str | None = None
    chapter_number: str | None = None
    topic: str | None = None
    made_by: str | None = None
    questions: str | None = None
    duration: str | None = None
    marks: str | None = None
    document_title: str | None = None
    document_url: str | None = None
    pdf_title: str | None = None
    pdf_url: str | None = None
    app_status: str | None = None
    test_date_status: str | None = None
    result_dashboard: str | None = None
    video_solution_update: str | None = None
    remarks: str | None = None
    search_text: str | None = None
    fingerprint: str
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class TestStatusBucket(BaseModel):
    label: str
    total: int
    done: int
    pending: int
    not_due: int = 0


class TestDataQuality(BaseModel):
    total: int
    missing_course: int = 0
    missing_class: int = 0
    missing_subject: int = 0
    missing_topic: int = 0
    missing_file_name: int = 0
    missing_clickable_link: int = 0
    missing_app_status: int = 0
    missing_test_date: int = 0
    missing_result_dashboard: int = 0
    missing_video_solution: int = 0




class TestCycleSummary(BaseModel):
    window_start: datetime
    window_end: datetime
    sunday_date: date
    result_deadline: datetime
    video_deadline: datetime
    window_open: bool
    total_tests: int = 0
    app_done: int = 0
    app_pending: int = 0
    subject_counts: dict[str, int] = Field(default_factory=dict)
    class_counts: dict[str, int] = Field(default_factory=dict)
    course_counts: dict[str, int] = Field(default_factory=dict)

class TestMonitorSummary(BaseModel):
    total_tests: int
    new_tests_7days: int
    app_status: TestStatusBucket
    result_dashboard: TestStatusBucket
    video_solution: TestStatusBucket
    sheet_counts: dict[str, int] = Field(default_factory=dict)
    subject_counts: dict[str, int] = Field(default_factory=dict)
    class_counts: dict[str, int] = Field(default_factory=dict)
    course_counts: dict[str, int] = Field(default_factory=dict)
    tests_with_clickable_files: int = 0
    tests_without_clickable_files: int = 0
    scheduled_tests: int = 0
    data_quality: TestDataQuality
    generated_at: datetime


class TestMonitorResponse(BaseModel):
    summary: TestMonitorSummary
    cycle: TestCycleSummary
    upcoming_sunday_tests: list[TestRecord] = Field(default_factory=list)
    pending_app: list[TestRecord] = Field(default_factory=list)
    pending_result: list[TestRecord] = Field(default_factory=list)
    pending_video: list[TestRecord] = Field(default_factory=list)
    recent_tests: list[TestRecord] = Field(default_factory=list)


class TestNotificationPresetRequest(BaseModel):
    channel: str = "whatsapp_personal"
    recipient: str
    source_id: str | None = None
    app_status_time: str = "18:00"
    result_time: str = "18:00"
    video_time: str = "18:00"


class ChangeField(BaseModel):
    field_name: str
    change_type: ChangeType
    old_value: str | None = None
    new_value: str | None = None
    coordinate: str | None = None
    row_number: int | None = None


class ChangeRecord(BaseModel):
    id: str
    source_id: str
    workbook_name: str
    sheet_name: str
    coordinate: str
    change_type: ChangeType
    old_value: str | None = None
    new_value: str | None = None
    detected_at: datetime
    field_name: str | None = None
    row_label: str | None = None
    category: str | None = None
    summary: str | None = None
    impact: str | None = None
    plain_location: str | None = None
    details: list[ChangeField] = Field(default_factory=list)
    affected_rows: list[int] = Field(default_factory=list)
    affected_count: int = 0
    group_kind: str | None = None


class ChangeSummary(BaseModel):
    added: int = 0
    updated: int = 0
    deleted: int = 0
    total: int = 0
    sources_checked: int = 0


class SyncResult(BaseModel):
    source_id: str
    status: str
    started_at: datetime
    completed_at: datetime
    live_data: bool
    workbook_profile: WorkbookProfile | None = None
    timetable_count: int = 0
    content_count: int = 0
    change_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    test_record_count: int = 0
    new_test_ids: list[str] = Field(default_factory=list)




class SyncStartResponse(BaseModel):
    source_id: str
    status: str
    message: str


class DashboardSummary(BaseModel):
    connected_sources: int
    tabs_scanned: int
    timetable_entries: int
    content_items: int
    videos: int
    pdfs: int
    changes_today: int
    sync_errors: int
    last_successful_sync: datetime | None


class NotificationRule(BaseModel):
    id: str
    name: str = Field(min_length=2, max_length=120)
    enabled: bool = True
    event_type: str
    send_time: str | None = "07:00"
    weekday: int | None = Field(default=0, ge=0, le=6)
    minutes_before: int | None = Field(default=None, ge=0, le=10080)
    timezone: str = "Asia/Kolkata"
    channels: list[str] = Field(default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    sheet_names: list[str] = Field(default_factory=list)
    include_pdf: bool = False
    include_excel: bool = False
    created_at: datetime

    @field_validator("send_time")
    @classmethod
    def validate_send_time(cls, value: str | None) -> str | None:
        if value in {None, ""}:
            return None
        try:
            parsed = time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Notification time must use HH:MM format") from exc
        return parsed.strftime("%H:%M")

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, channels: list[str]) -> list[str]:
        allowed = {"email", "telegram", "google_chat", "whatsapp", "whatsapp_personal", "push"}
        unknown = set(channels) - allowed
        if unknown:
            raise ValueError(f"Unsupported notification channels: {sorted(unknown)}")
        return sorted(set(channels))


class NotificationDelivery(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    channel: str
    recipient: str
    status: str
    message: str
    error: str | None = None
    attempted_at: datetime
    scheduled_for: datetime | None = None
    is_test: bool = False
    dedupe_key: str


class NotificationStatus(BaseModel):
    scheduler_active: bool
    scheduler_interval_seconds: int
    sheet_refresh_minutes: int
    page_refresh_minutes: int
    configured_channels: dict[str, bool]


class NotificationTestResponse(BaseModel):
    rule_id: str
    scheduler_ok: bool
    preview: str
    deliveries: list[NotificationDelivery]




class QrDesignSettings(BaseModel):
    foreground_color: str = "#111827"
    background_color: str = "#FFFFFF"
    dot_style: Literal["square", "rounded", "dots"] = "rounded"
    marker_border_style: Literal["square", "rounded", "circle"] = "rounded"
    marker_center_style: Literal["square", "rounded", "circle"] = "square"
    marker_border_color: str | None = None
    marker_center_color: str | None = None
    frame_style: Literal["none", "text", "badge"] = "text"
    frame_text: str | None = Field(default="SCAN ME", max_length=42)
    logo_asset_id: str | None = Field(default=None, max_length=80)
    logo_scale_percent: int = Field(default=18, ge=8, le=32)
    logo_background: bool = True


class QrScanExperience(BaseModel):
    mode: Literal["brand", "logo", "page"] = "brand"
    asset_id: str | None = Field(default=None, max_length=80)
    title: str = Field(default="Opening…", max_length=80)
    message: str = Field(default="Preparing your QR action", max_length=160)
    accent_color: str = "#2563EB"
    background_color: str = "#F8FAFC"
    redirect_delay_ms: int = Field(default=900, ge=650, le=5000)
    logo_scale_percent: int = Field(default=28, ge=15, le=65)
    image_fit: Literal["cover", "contain"] = "cover"
    image_scale_percent: int = Field(default=100, ge=35, le=100)


QrCodeType = Literal["url", "calendar", "contact", "email", "geo", "phone", "wifi"]
QrTrackingMode = Literal["tracked", "direct"]
QrIdentityMode = Literal["anonymous", "email"]


class QrCodeCreate(BaseModel):
    qr_type: QrCodeType = "url"
    tracking_mode: QrTrackingMode = "tracked"
    identity_mode: QrIdentityMode = "anonymous"
    target_url: HttpUrl | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    name: str | None = Field(default=None, max_length=120)
    design: QrDesignSettings = Field(default_factory=QrDesignSettings)
    experience: QrScanExperience = Field(default_factory=QrScanExperience)


class QrCodeUpdate(BaseModel):
    qr_type: QrCodeType | None = None
    tracking_mode: QrTrackingMode | None = None
    identity_mode: QrIdentityMode | None = None
    target_url: HttpUrl | None = None
    content: dict[str, Any] | None = None
    name: str | None = Field(default=None, max_length=120)
    design: QrDesignSettings | None = None
    experience: QrScanExperience | None = None


class QrPreviewRequest(BaseModel):
    target_url: HttpUrl | None = None
    design: QrDesignSettings = Field(default_factory=QrDesignSettings)


class QrCodeRecord(BaseModel):
    id: str
    name: str
    slug: str
    qr_type: QrCodeType = "url"
    tracking_mode: QrTrackingMode = "tracked"
    identity_mode: QrIdentityMode = "anonymous"
    target_url: str
    content: dict[str, Any] = Field(default_factory=dict)
    public_base_url: str | None = None
    short_url: str | None = None
    active: bool = True
    design: QrDesignSettings = Field(default_factory=QrDesignSettings)
    experience: QrScanExperience = Field(default_factory=QrScanExperience)
    template_id: str | None = None
    template_name: str | None = None
    created_at: datetime
    updated_at: datetime
    total_scans: int = 0
    unique_visitors: int = 0
    unique_emails: int = 0
    country_count: int = 0
    legacy_scans: int = 0


class QrTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=240)
    tracking_mode: QrTrackingMode = "tracked"
    identity_mode: QrIdentityMode = "anonymous"
    design: QrDesignSettings = Field(default_factory=QrDesignSettings)
    experience: QrScanExperience = Field(default_factory=QrScanExperience)
    is_default: bool = False


class QrTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=240)
    tracking_mode: QrTrackingMode | None = None
    identity_mode: QrIdentityMode | None = None
    design: QrDesignSettings | None = None
    experience: QrScanExperience | None = None
    is_default: bool | None = None


class QrTemplateRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    tracking_mode: QrTrackingMode = "tracked"
    identity_mode: QrIdentityMode = "anonymous"
    design: QrDesignSettings = Field(default_factory=QrDesignSettings)
    experience: QrScanExperience = Field(default_factory=QrScanExperience)
    is_default: bool = False
    qr_count: int = 0
    created_at: datetime
    updated_at: datetime


class QrBulkItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: HttpUrl


class QrBulkCreateRequest(BaseModel):
    template_id: str = Field(min_length=8, max_length=80)
    items: list[QrBulkItem] = Field(min_length=1, max_length=500)


class QrBulkCreateResponse(BaseModel):
    template: QrTemplateRecord
    created: list[QrCodeRecord]
    count: int


class QrAssetResponse(BaseModel):
    id: str
    url: str
    width: int
    height: int


class QrResolveResponse(BaseModel):
    qr_type: QrCodeType
    action_kind: str
    action_url: str | None = None
    experience: QrScanExperience
    identity_mode: QrIdentityMode = "anonymous"
    wifi: dict[str, Any] | None = None


class QrAnonymousTelemetry(BaseModel):
    browser_version: str | None = Field(default=None, max_length=80)
    platform_version: str | None = Field(default=None, max_length=80)
    architecture: str | None = Field(default=None, max_length=32)
    bitness: str | None = Field(default=None, max_length=16)
    form_factors: list[str] = Field(default_factory=list)
    device_memory_gb: float | None = Field(default=None, ge=0, le=1024)
    hardware_concurrency: int | None = Field(default=None, ge=0, le=1024)
    max_touch_points: int | None = Field(default=None, ge=0, le=100)
    pixel_ratio: float | None = Field(default=None, ge=0, le=20)
    color_depth: int | None = Field(default=None, ge=0, le=128)
    viewport_width: int | None = Field(default=None, ge=0, le=20000)
    viewport_height: int | None = Field(default=None, ge=0, le=20000)
    screen_orientation: str | None = Field(default=None, max_length=40)
    connection_type: str | None = Field(default=None, max_length=40)
    effective_connection_type: str | None = Field(default=None, max_length=40)
    downlink_mbps: float | None = Field(default=None, ge=0, le=100000)
    rtt_ms: int | None = Field(default=None, ge=0, le=600000)
    save_data: bool | None = None
    languages: list[str] = Field(default_factory=list)
    cookies_enabled: bool | None = None
    browser_vendor: str | None = Field(default=None, max_length=80)
    timezone_offset_minutes: int | None = Field(default=None, ge=-1440, le=1440)
    standalone: bool | None = None
    primary_pointer: str | None = Field(default=None, max_length=20)
    hover_capable: bool | None = None
    color_gamut: str | None = Field(default=None, max_length=20)


class QrScanConfirm(BaseModel):
    visitor_id: str = Field(min_length=8, max_length=160)
    event_id: str = Field(min_length=8, max_length=160)
    source_tag: str | None = Field(default=None, max_length=40)
    referrer: str | None = Field(default=None, max_length=600)
    language: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default=None, max_length=80)
    screen_width: int | None = Field(default=None, ge=0, le=20000)
    screen_height: int | None = Field(default=None, ge=0, le=20000)
    scanner_email: str | None = Field(default=None, max_length=254)
    device_model: str | None = Field(default=None, max_length=120)
    client_platform: str | None = Field(default=None, max_length=120)
    telemetry: QrAnonymousTelemetry = Field(default_factory=QrAnonymousTelemetry)


class QrScanRecord(BaseModel):
    id: int
    qr_id: str
    qr_name: str
    scanned_at: datetime
    country: str
    device_type: str
    browser: str
    operating_system: str = "Other"
    device_model: str = ""
    device_id: str = ""
    scanner_email: str = ""
    platform: str = "Direct / QR"
    source_confidence: str = "unknown"
    referrer_host: str = ""
    language: str = ""
    timezone: str = ""
    screen_resolution: str = ""
    client_platform: str = ""
    browser_version: str = ""
    platform_version: str = ""
    architecture: str = ""
    bitness: str = ""
    device_memory_gb: float | None = None
    hardware_concurrency: int | None = None
    max_touch_points: int | None = None
    pixel_ratio: float | None = None
    viewport: str = ""
    viewport_width: int | None = None
    viewport_height: int | None = None
    color_depth: int | None = None
    connection: str = ""
    network_quality: str = ""
    form_factors: str = ""
    screen_orientation: str = ""
    browser_vendor: str = ""
    cookies_enabled: bool | None = None
    standalone: bool | None = None
    input_capability: str = ""
    color_gamut: str = ""
    languages: str = ""
    timezone_offset_minutes: int | None = None


class QrDeviceSummary(BaseModel):
    device_id: str
    scans: int
    first_seen: datetime
    last_seen: datetime
    device_type: str
    operating_system: str
    browser: str
    device_model: str = ""
    scanner_email: str = ""
    client_platform: str = ""
    language: str = ""
    timezone: str = ""
    screen_resolution: str = ""
    countries: int = 0
    qr_codes: int = 0
    browser_version: str = ""
    platform_version: str = ""
    architecture: str = ""
    bitness: str = ""
    device_memory_gb: float | None = None
    hardware_concurrency: int | None = None
    max_touch_points: int | None = None
    pixel_ratio: float | None = None
    viewport: str = ""
    viewport_width: int | None = None
    viewport_height: int | None = None
    color_depth: int | None = None
    connection: str = ""
    network_quality: str = ""
    form_factors: str = ""
    screen_orientation: str = ""
    browser_vendor: str = ""
    cookies_enabled: bool | None = None
    standalone: bool | None = None
    input_capability: str = ""
    color_gamut: str = ""
    languages: str = ""
    timezone_offset_minutes: int | None = None


class QrAnalyticsSummary(BaseModel):
    total_qr_codes: int = 0
    active_qr_codes: int = 0
    total_scans: int = 0
    unique_visitors: int = 0
    unique_emails: int = 0
    identified_scans: int = 0
    anonymous_scans: int = 0
    scans_today: int = 0
    scans_7days: int = 0
    scans_30days: int = 0
    bot_scans: int = 0
    legacy_scans: int = 0
    countries: dict[str, int] = Field(default_factory=dict)
    devices: dict[str, int] = Field(default_factory=dict)
    browsers: dict[str, int] = Field(default_factory=dict)
    operating_systems: dict[str, int] = Field(default_factory=dict)
    device_models: dict[str, int] = Field(default_factory=dict)
    memory_classes: dict[str, int] = Field(default_factory=dict)
    cpu_cores: dict[str, int] = Field(default_factory=dict)
    connection_types: dict[str, int] = Field(default_factory=dict)
    platforms: dict[str, int] = Field(default_factory=dict)
    attribution_confidence: dict[str, int] = Field(default_factory=dict)
    daily: dict[str, int] = Field(default_factory=dict)
    top_devices: list[QrDeviceSummary] = Field(default_factory=list)
    recent_scans: list[QrScanRecord] = Field(default_factory=list)


class PaginatedResponse(BaseModel):
    items: list[Any]
    page: int
    page_size: int
    total: int
    pages: int


class ContentSearchResponse(PaginatedResponse):
    search_ms: int
    normalized_query: str | None = None
