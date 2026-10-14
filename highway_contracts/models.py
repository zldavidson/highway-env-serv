"""JSON-safe data contract for source-specific opportunity discovery.

Adapters must supply authoritative IDs and redact sensitive source material
before constructing evidence. These models never infer timezone or identity.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from urllib.parse import urlsplit


def _timestamp(value: str | None) -> None:
    if value is not None:
        datetime.fromisoformat(value)


class Payload:
    def to_dict(self) -> dict:
        result = asdict(self)
        # Reject non-JSON checkpoint values and non-finite numbers.
        json.dumps(result, allow_nan=False)
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), allow_nan=False)


@dataclass(kw_only=True)
class Evidence(Payload):
    url: str
    field: str
    raw_text: str
    observed_at: str
    method: str
    confidence: float
    page: int | None = None

    def __post_init__(self):
        _timestamp(self.observed_at)
        if self.method not in {'source', 'parsed', 'derived'}:
            raise ValueError('Invalid evidence method')
        if not 0 <= self.confidence <= 1:
            raise ValueError('Evidence confidence must be between 0 and 1')
        if urlsplit(self.url).username is not None or urlsplit(self.url).password is not None:
            raise ValueError('Evidence URLs must not contain credentials')


@dataclass(kw_only=True)
class Attachment(Payload):
    url: str
    title: str
    kind: str
    source_attachment_id: str | None = None
    evidence: list[Evidence] = field(default_factory=list)

    def __post_init__(self):
        if self.kind not in {'scope', 'addendum', 'form', 'other'}:
            raise ValueError('Invalid attachment kind')


@dataclass(kw_only=True)
class Opportunity(Payload):
    source: str
    source_id: str
    source_url: str
    title: str
    observed_at: str
    agency: str | None = None
    state: str | None = None
    solicitation_number: str | None = None
    notice_type: str | None = None
    source_status: str | None = None
    status: str = 'unknown'
    published_at: str | None = None
    updated_at: str | None = None
    deadline_at: str | None = None
    deadline_raw: str | None = None
    deadline_timezone: str | None = None
    naics: list[str] = field(default_factory=list)
    set_aside: str | None = None
    attachments: list[Attachment] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def __post_init__(self):
        if not self.source_id.strip():
            raise ValueError('An authoritative ID or documented detail URL fallback is required')
        if self.status not in {'unknown', 'upcoming', 'open', 'closed', 'awarded', 'cancelled'}:
            raise ValueError('Invalid opportunity status')
        for value in (self.observed_at, self.published_at, self.updated_at, self.deadline_at):
            _timestamp(value)
        if self.deadline_at is not None:
            deadline = datetime.fromisoformat(self.deadline_at)
            if deadline.utcoffset() is None:
                raise ValueError('Ambiguous deadlines belong in deadline_raw with timezone=None')


@dataclass(kw_only=True)
class Diagnostic(Payload):
    code: str
    message: str
    severity: str
    retryable: bool
    url: str | None = None

    def __post_init__(self):
        if self.severity not in {'info', 'warning', 'error'}:
            raise ValueError('Invalid diagnostic severity')


def detail_url_identity(url: str) -> tuple[str, Diagnostic]:
    """Explicit fallback for sources which provide no authoritative notice ID."""
    from .crawler import canonical

    normalized = canonical(url)
    if normalized is None:
        raise ValueError('A stable HTTPS detail URL is required')
    return normalized, Diagnostic(
        code='source_id_url_fallback',
        message='Source lacks an authoritative ID; normalized detail URL used as source_id.',
        url=normalized, severity='warning', retryable=False,
    )


def _counts() -> dict[str, int]:
    return dict.fromkeys(('listing_records_seen', 'detail_records_fetched',
                          'opportunities_emitted', 'attachment_links_seen'), 0)


@dataclass(kw_only=True)
class DiscoveryBatch(Payload):
    opportunities: list[Opportunity] = field(default_factory=list)
    next_checkpoint: dict | None = None
    complete: bool = False
    diagnostics: list[Diagnostic] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=_counts)

    def __post_init__(self):
        self.counts = {**_counts(), **self.counts}
        if any(type(value) is not int or value < 0 for value in self.counts.values()):
            raise ValueError('Counts must be nonnegative integers')
        self.to_dict()
        if any(d.code == 'verified_empty' for d in self.diagnostics) and not self.verified_empty:
            raise ValueError('verified_empty requires a complete empty batch without blocking diagnostics')

    @property
    def verified_empty(self) -> bool:
        blocking = {'authentication_required', 'blocked', 'parser_error',
                    'transport_error', 'truncated', 'unsupported'}
        return (self.complete and not self.opportunities
                and not any(d.code in blocking or d.severity == 'error' for d in self.diagnostics))
