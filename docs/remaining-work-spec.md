# Remaining-work specification

Parallel delivery: [individual Codex chat assignments](parallel-agent-plan.md) define file ownership, branches, launch waves, merge order and copy/paste prompts. [Adapter contract v1](adapter-contract-v1.md) freezes the shared interfaces so source agents can implement independently.

## Objective and current boundary

Collect highway vegetation, landscaping, grounds, and related environmental-services opportunities across MD, VA, PA, FL, UT, WA, and CA, plus federal work performed in those states. Qualified leads must link to authoritative scope, deadline, and original attachments.

Implemented: bounded HTML discovery, scoped HTTPS downloads, robots rules, retry/backoff, conditional HTTP caching, hashing, PDF originals, page-level extraction, version retention, latest-observed-version full-text search, CSV export, and crawl reports. Routine operations use no LLM calls.

Not established: complete state coverage, verified open-bid status, deadlines, OCR, or portal-specific pagination. The source configurations are provisional seeds. A successful HTML fetch is not evidence of complete collection.

## 1. Source-specific adapters (highest priority)

Define an adapter interface returning normalized opportunities, attachment URLs, next checkpoint, and diagnostics. Keep fetching and indexing shared. Commit checkpoints only after records persist. Mark each adapter supported, experimental, authentication-required, or blocked.

| State | Required collection |
|---|---|
| Maryland | eMMA public search, pagination, details and attachments; optional authorized vendor session |
| Virginia | eVA/VBO goods/services filtered to VDOT; retain VDOT advertisements |
| Pennsylvania | eMarketplace forms, agency filters, pagination, details and FileDownload links; evaluate ECMS separately |
| Florida | Districts 1–7 and Turnpike maintenance lettings, PDFs, addenda; evaluate statewide services portal |
| Utah | U3P/Bonfire public listings/details, browser adapter if required |
| Washington | WSDOT public works plus WEBS goods/services through authorized access |
| California | Cal eProcure Caltrans notices/details/attachments plus public Caltrans evidence pages |

Prefer documented APIs/exports, then HTTP parsing, then browser automation. Undocumented browser endpoints are not supported public APIs. Do not bypass authentication, access blocks, or CAPTCHA; report access limitations.

Acceptance: fixture tests for pagination, amendments, empty results and attachments; documented live smoke runs; counts reconciled against visible listings for a defined date range; run reports record filters, time windows and pagination exhaustion. On a qualified detail page, download all relevant attachments even when link labels lack vegetation terms. Zero results must be distinguished from parser/access failure.

## 2. SAM.gov API adapter

Use the current documented API with SAM_API_KEY from environment variables. Never store or log credentials. Search NAICS 561730 plus broader keywords for miscoded work, filtered to seven target states; record unknown locations for review. Persist notice IDs, versions, descriptions, accessible attachments and source links. Respect actual account rate limits.

Acceptance: pagination, throttling and key-redaction tests; credential-free unit suite; real keyed smoke run when credentials are available; reconciliation to a defined public search.

## 3. Opportunity schema and lifecycle

Add opportunity, notice_version, attachment, opportunity_attachment, source_run and source_health tables. Fields: source ID, agency, title, solicitation number, notice type, location, source status, normalized status, publication/update dates, deadline/timezone, set-aside, NAICS, source URL and observation times. Derived values need evidence and confidence. PDFs remain separate from opportunities.

Statuses: unknown, upcoming, open, closed, awarded, cancelled. Missing/ambiguous deadlines remain unknown. Preserve addenda and superseded records. Latest observed is not necessarily latest authoritative after a failed fetch. Missing from one listing must not imply cancellation.

Acceptance: idempotent upserts; extended deadlines; reappearing notices; expired/deleted listings; timezone ambiguity; no duplicate leads. Migrate the earlier prototype database with a tested backup and no unnecessary redownloads.

## 4. Local OCR and extraction quality

Detect scanned/mixed pages and integrate optional local OCR after capability detection. Keep originals and derivatives separate, retain original page numbering and extraction-method/version metadata. Avoid OCR for legible pages. Structured table/pay-item extraction requires original-page evidence and its own validation.

Acceptance: image-only, mixed, rotated and malformed fixtures; searchable scanned scope text; original page links; extraction failures recorded individually. A low-character heuristic alone is insufficient to detect all scanned content.

## 5. Deterministic relevance

Configure weighted rules for mowing, groundskeeping, landscaping, brush/tree work, irrigation, invasive plants, planting, revegetation and erosion control. Environmental terms broaden discovery but must not alone qualify leads. Prefer title, scope and pay items over boilerplate. Down-rank unrelated waste hauling, consulting, building maintenance and construction-only notices. Habitat/ecosystem restoration is an optional related category.

Acceptance: labeled positives/negatives with reported precision/recall and sample size; matched-rule explanations and evidence pages; user-overridable filters. No broad quality claim based on a tiny fixture set.

## 6. Reliability, packaging and operations

Add config validation, schema migrations, concurrency locks, resumable queues, graceful interruption, cache retention/disk quotas, backup/restore and request metrics. Add dependency lockfiles and CI on Windows/Linux. Expand network tests for 304, 429/Retry-After, timeout, redirects, robots failures, invalid/oversized PDFs and HTML encodings. Validate a clean package installation.

Acceptance: safe interrupted/resumed runs; concurrent writers rejected; unchanged documents not re-extracted; changed PDFs preserve history and update current search; partial failures return actionable nonzero status; reproducible installation/tests.

## 7. Scheduling and notifications

Document Windows Task Scheduler and optional cron/container deployments. Do not install schedules implicitly. Notifications require explicit channel authorization; include only new/changed qualified leads, deadline changes, failures or required action. Deduplicate deliveries and remain quiet on unchanged runs.

Acceptance: dry-run previews; new/amended notice tests; timezone-correct deadline reminders; failure notifications identify the affected source; no credentials in reports.

## 8. Review UI and optional semantic search

Local dashboard: source health, opportunity filters, PDF/page evidence, deadline sorting, saved searches, exports and review decisions. Show facts separately from extracted claims. Full-text remains default. Introduce local embeddings only after labeled queries demonstrate improved recall; embed changed chunks only. Optional LLM summaries must be cached by hash, evidence-linked and disabled by default.

Acceptance: zero-model-token collection/index/search; visible failed/unknown states; measured retrieval improvement before embeddings; generated summaries are never authoritative eligibility/deadline data.

## Delivery sequence and completion

1. Validate one complete state adapter with live reconciliation and metadata.
2. Add lifecycle schema/rules and migration, then remaining state adapters.
3. Add federal API and OCR as access/data require.
4. Harden operations and scheduling.
5. Add review UI; assess semantic search against actual retrieval needs.

Complete means all seven states have tested adapters or explicit access limitations; supported sources pass live reconciliation; repeats collect changes without duplicate leads or repeated extraction; original page evidence and status uncertainty remain visible; routine operations require no model inference.
