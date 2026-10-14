from __future__ import annotations

from datetime import timedelta, timezone

# India has used a fixed UTC+05:30 civil offset since 1945 and does not use DST.
# A fixed offset keeps the local Windows build independent of an external IANA
# timezone database, which is not bundled with some Python distributions.
INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")
