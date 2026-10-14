# Frozen parallel implementation contract v1

This document specifies interfaces for parallel implementation; they are not yet runtime code. The core agent implements models.py. Integration owns changes to this document. Agents must not silently alter names/types.

## Plain-data models

Use Python dataclasses and JSON-serializable values; use strings for enums in serialized payloads. All timestamps use ISO 8601 with offsets when known. Never attach a timezone to an ambiguous local timestamp by guessing; retain raw text and timezone=null. IDs come from authoritative source IDs, not titles.

- `Evidence`: `url: str`, `field: str`, `raw_text: str`, `page: int | None = None`, `observed_at: str`, `method: str` (source/parsed/derived), `confidence: float` (0–1).
- `Attachment`: `url: str`, `title: str`, `kind: str` (scope/addendum/form/other), `source_attachment_id: str | None`, `evidence: list[Evidence]`.
- `Opportunity`: `source: str`, `source_id: str`, `source_url: str`, `title: str`, `agency: str | None`, `state: str | None`, `solicitation_number: str | None`, `notice_type: str | None`, `source_status: str | None`, `status: str` (unknown/upcoming/open/closed/awarded/cancelled), `published_at: str | None`, `updated_at: str | None`, `deadline_at: str | None`, `deadline_raw: str | None`, `deadline_timezone: str | None`, `naics: list[str]`, `set_aside: str | None`, `attachments: list[Attachment]`, `evidence: list[Evidence]`, `observed_at: str`.
- `Diagnostic`: `code: str`, `message: str`, `url: str | None`, `severity: str` (info/warning/error), `retryable: bool`. Codes must distinguish authentication_required, blocked, parser_error, transport_error, verified_empty, truncated and unsupported.
- `DiscoveryBatch`: `opportunities: list[Opportunity]`, `next_checkpoint: dict | None`, `complete: bool`, `diagnostics: list[Diagnostic]`, `counts: dict[str,int]`. Counts include listing_records_seen, detail_records_fetched, opportunities_emitted and attachment_links_seen. Empty is verified only when complete=true and no blocking/parser diagnostics.

Optional Opportunity fields default to None, arrays to new empty lists, status to unknown. A source lacking authoritative IDs may use a stable normalized detail URL, with an explicit diagnostic documenting the fallback. Do not collapse different notices by similar titles. Evidence must not contain credentials, cookies or sensitive response fields.

## Adapter interface

Each module exposes `SOURCE_ID: str`, `capabilities() -> dict`, and `discover(client, config: dict, checkpoint: dict | None = None) -> DiscoveryBatch`.

One call yields a bounded batch, with an opaque JSON checkpoint to continue. An adapter does not write database tables or download/index PDFs. Pipeline persists emitted metadata/checkpoint atomically, then separately downloads attachments and records per-attachment outcomes. Do not discard an opportunity merely because one attachment failed. Complete means the configured window/filter exhausted, not all historical source records.

Capabilities includes mode (http/api/browser), support (experimental/supported/authentication_required/blocked), channels_covered, channels_missing, credentials_required, and live_verified_at (nullable).

Adapters must expose fixture-testable parsers and use dependency injection. For work before models.py exists, tests may use task-local temporary model stubs; do not commit competing shared model definitions. Integration runs tests against core models before merge.

## Fetch client interface

`client.fetch(url: str, *, method: str = 'GET', params: dict | None = None, data: bytes | None = None, headers: dict | None = None) -> FetchResponse`.

`FetchResponse`: url (final URL), status (HTTP status, with 304 normalized to cached successful content), headers (mapping), body (bytes), from_cache (bool). Provide `text()` respecting declared charset and `json()` helpers. Errors expose code, sanitized URL and retryability; actual credentials never appear in errors/logs. Test fakes implement this interface without networking.

GET params append without destroying existing query parameters. Cache identity includes method and request content; authenticated results must not share an anonymous cache. GET conditional caching is supported; POST search forms require explicit cache policy. Source config defines exact allowed hosts, delay, byte/request limits, date window and agency filters. POST/API credentials are optional source-specific inputs and excluded from serialized config/evidence.

The client enforces budgets, robots policy for scraping, redirects and network timeouts. Official API use follows its documented policy. Any needed exception to default robots handling must be documented and implemented by transport/integration, not improvised within a state adapter.

## Extraction interface

`extract_pdf(original_path: Path, *, output_dir: Path, ocr: str = 'auto') -> ExtractionResult`.

Result: original_path, derivative_path (optional), engine_version, pages (list of page_number/text/method/quality_flags), diagnostics. Page numbers are one-based original PDF pages. OCR mode auto/off/required; unavailable OCR in auto produces actionable quality flags without claiming full extraction. Hash/engine-version caching is controlled by pipeline/store.

## Relevance interface

`score_opportunity(opportunity: Opportunity, pages: list[dict], rules: dict) -> RelevanceResult`.

Result: score (float), category (string), qualified (bool), matches (rule_id/weight/field/page/quote/source_url), diagnostics. Pages include document_id, page_number, text, source_url. Scoring must be deterministic and side-effect free; qualification is distinct from source status/eligibility. Never change deadlines or source facts while scoring.

## Persistence and integration

Core implements `upsert_batch(batch)` with transactional notice/checkpoint persistence, records attachment outcomes separately, and invokes extraction/scoring through the interfaces. Adapter identity is `(source, source_id)`; notice and attachment changes retain version history. Failed runs must not advance to an unpersisted checkpoint or mark missing opportunities cancelled. Existing Store APIs remain supported until integration updates their callers/tests.

Integration alone updates package dependencies, registries, shared source config and package init files. Per-source config is `config/adapters/<task-id>.json`; agents must not amend the shared config directly. Fixture tests must run offline without credentials or browser installation unless explicitly marked optional integration tests.
