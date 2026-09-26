# v1.0.24 Backend Implementation Map

This is the public, sanitized continuation map for the private runtime implementation.

## Models

The runtime adds these Pydantic contracts in `services/api/app/models.py`:

```python
class QrTemplateCreate(BaseModel):
    name: str
    description: str = ""
    tracking_mode: QrTrackingMode = "tracked"
    identity_mode: QrIdentityMode = "anonymous"
    design: QrDesignSettings = Field(default_factory=QrDesignSettings)
    experience: QrScanExperience = Field(default_factory=QrScanExperience)
    is_default: bool = False

class QrTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tracking_mode: QrTrackingMode | None = None
    identity_mode: QrIdentityMode | None = None
    design: QrDesignSettings | None = None
    experience: QrScanExperience | None = None
    is_default: bool | None = None

class QrTemplateRecord(BaseModel):
    id: str
    name: str
    description: str
    tracking_mode: QrTrackingMode
    identity_mode: QrIdentityMode
    design: QrDesignSettings
    experience: QrScanExperience
    is_default: bool
    qr_count: int
    created_at: datetime
    updated_at: datetime

class QrBulkItem(BaseModel):
    name: str
    url: HttpUrl

class QrBulkCreateRequest(BaseModel):
    template_id: str
    items: list[QrBulkItem] = Field(min_length=1, max_length=500)

class QrBulkCreateResponse(BaseModel):
    template: QrTemplateRecord
    count: int
    created: list[QrCodeRecord]
```

`QrCodeRecord` also carries optional `template_id` and `template_name` provenance.

## Database

Migration adds `template_id` to `qr_codes` before creating any dependent index.

The new table is conceptually:

```sql
CREATE TABLE IF NOT EXISTS qr_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    tracking_mode TEXT NOT NULL DEFAULT 'tracked',
    identity_mode TEXT NOT NULL DEFAULT 'anonymous',
    design_json TEXT NOT NULL,
    experience_json TEXT NOT NULL,
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Runtime database methods:

```python
create_qr_template(...)
list_qr_templates(...)
get_qr_template(template_id)
update_qr_template(template_id, ...)
delete_qr_template(template_id)
create_qr_codes_bulk(template, items)
qr_asset_reference_count(asset_id)
```

Deleting a template executes the equivalent of:

```sql
UPDATE qr_codes SET template_id = NULL WHERE template_id = ?;
DELETE FROM qr_templates WHERE id = ?;
```

This preserves already-issued QR codes and their analytics.

## API routes

Implemented in `services/api/app/api/routes.py`:

```text
GET    /api/v1/qr-templates
GET    /api/v1/qr-templates/{template_id}
POST   /api/v1/qr-templates
PATCH  /api/v1/qr-templates/{template_id}
POST   /api/v1/qr-templates/{template_id}/duplicate
DELETE /api/v1/qr-templates/{template_id}
POST   /api/v1/qr-bulk
```

Important API rules:

```python
if template.tracking_mode != "tracked":
    raise HTTPException(422, "Tracked template is required for Bulk QR analytics")

if len({item.name.casefold() for item in items}) != len(items):
    raise HTTPException(422, "Duplicate QR names in one bulk request are not allowed")
```

For each bulk item the runtime generates a new campaign ID + unique compact slug, copies the template design/experience/tracking/identity snapshot, and stores `template_id` provenance.

## Independent analytics contract

Analytics remain campaign-scoped:

```text
GET /api/v1/qr-analytics?qr_id=<QR_ID>
```

The permanent test proves:

```python
scan(qr_a)
assert analytics(qr_a)["total_scans"] == 1
assert analytics(qr_b)["total_scans"] == 0
```

Sharing a template never shares scan counters.

## Asset reference safety

Logo/background cleanup checks references across both `qr_codes` and `qr_templates`. A physical uploaded asset is deleted only when no remaining QR or template refers to it.

## Windows acceptance

The installer creates a temporary tracked template, bulk-creates A/B, scans only A, verifies A=1 and B=0, deletes the template, verifies QR A still exists with its original target, then cleans the temporary campaigns. Any failure triggers rollback.