# Parallel Codex chat assignments

Repository: https://github.com/zldavidson/highway-env-serv.git

## Launch procedure

The local starter and specs must first be committed and pushed to a shared baseline branch. At the time this plan was written, the remote was empty and the local files were uncommitted. Do not launch remote agents against an empty repository. Record the baseline commit SHA here or in each assignment before starting.

Give each chat its own clone or managed Git worktree and task branch from the SAME baseline SHA. Do not share one checkout, .git index, virtual environment, or writable data directory between chats. Use `data/<task-id>/` for task-specific live runs. Agents can work in their own chats; no inter-chat messaging is required. Each returns a PR or branch/commit and a handoff report. One integration chat merges work in the order below.

Do not have multiple chats update README.md, pyproject.toml, config/sources.json, highway_contracts/cli.py, crawler.py, store.py, or the shared contracts. File ownership below controls this. An agent needing an out-of-scope edit records a proposed change in its handoff; the owner/integrator applies it. Never overwrite another agent's work to resolve a conflict.

## Shared instructions for every assignment

Read README.md, docs/remaining-work-spec.md, docs/adapter-contract-v1.md, and this plan. Routine scraping, extraction, scoring and search must use zero LLM calls. Favor deterministic HTTP/API collection; introduce browser automation only when the source requires it. Preserve authoritative source links, unknown values and access failures. Do not invent open status, deadlines, coverage or opportunities.

Do not bypass robots rules, account restrictions, access blocks or CAPTCHA. Do not send notifications, create schedules, deploy, or alter account settings. Never commit credentials, session cookies, original downloaded PDF corpora, personal data, or runtime databases. Public fixtures should be small, representative and provenance-labeled; sanitize session/security fields.

Each deliverable includes code, source-specific offline tests, a minimal CLI/example, source notes, and a handoff. Distinguish implemented, fixture-validated, live-validated, and blocked functionality. Run existing tests plus task tests. A missing credential may block a live test but does not justify skipping fixture-based implementation. A source with zero records must report verified-empty vs incomplete/blocked/parser failure.

Handoff path: `docs/handoffs/<task-id>.md`. Include baseline SHA, branch/commit or PR, owned files changed, commands and outcomes, dependency proposals, live-run date/filter/window/counts, access limits, remaining work and integration instructions. Live evidence goes in `docs/evidence/<task-id>/`, with no secrets. No claims of complete state coverage without listing reconciliation.

## Ownership and work packages

| ID / branch | Owned paths | Assignment |
|---|---|---|
| core / agent/core | store.py, migrations/, models.py, pipeline.py, cli.py, tests/test_core*.py | Opportunity lifecycle, persistence, registry/CLI integration and prototype migration |
| transport / agent/transport | crawler.py, transport.py, tests/test_transport*.py | Fetching, retries/cache/robots, scoped redirects, crawl resumability interfaces |
| pa / agent/pa | adapters/pa.py, config/adapters/pa.json, tests/adapters/test_pa.py, fixtures/pa/ | PA eMarketplace search, pagination, details and attachments |
| fl / agent/fl | adapters/fl.py, config/adapters/fl.json, tests/adapters/test_fl.py, fixtures/fl/ | FDOT districts 1–7 and Turnpike maintenance lettings/addenda |
| va / agent/va | adapters/va.py, config/adapters/va.json, tests/adapters/test_va.py, fixtures/va/ | eVA/VBO VDOT goods/services plus advertisement links |
| md / agent/md | adapters/md.py, config/adapters/md.json, tests/adapters/test_md.py, fixtures/md/ | Maryland eMMA public solicitation collection |
| ut / agent/ut | adapters/ut.py, config/adapters/ut.json, tests/adapters/test_ut.py, fixtures/ut/ | Utah U3P/Bonfire public opportunities |
| wa / agent/wa | adapters/wa.py, config/adapters/wa.json, tests/adapters/test_wa.py, fixtures/wa/ | WSDOT public works and WEBS coverage/access assessment |
| ca / agent/ca | adapters/ca.py, config/adapters/ca.json, tests/adapters/test_ca.py, fixtures/ca/ | Cal eProcure/Caltrans service solicitations |
| sam / agent/sam | adapters/sam.py, config/adapters/sam.json, tests/adapters/test_sam.py, fixtures/sam/ | Federal API discovery for the seven states |
| relevance / agent/relevance | relevance.py, config/relevance.json, tests/test_relevance.py, fixtures/relevance/ | Explainable vegetation/environmental lead scoring |
| extraction / agent/extraction | extraction.py, tests/test_extraction.py, fixtures/extraction/ | Local PDF extraction/OCR interface and quality reporting |
| operations / agent/operations | operations/, tests/test_operations*.py, docs/operations.md | Single-writer lock, backups, run health, schedule dry-run templates |
| integration / agent/integration | shared contracts, package init files, pyproject.toml, locks, CI, README.md, config/sources.json, integration tests | Review/merge, dependencies, docs, cross-component verification |

All agents own their own handoff/evidence paths. Existing tests/test_pipeline.py belongs to integration. Adapters live under `highway_contracts/adapters/`; new component paths are relative to `highway_contracts/` unless explicitly docs/config/tests/fixtures/operations. The integration agent creates package __init__.py files; adapter agents must not create competing versions.

## Dependencies and concurrency

Wave 1 can run core, transport, all state adapters, SAM, relevance and extraction in parallel against the written contract. Adapter fixtures use fake fetch clients, so they do not wait for transport. Core tests use stub adapters, so they do not wait for state code. Extraction and relevance expose pure functions and do not edit store.py. Operations can draft/test helpers now but wires them after core/transport settle.

Recommended first batch if limiting chat count: core, transport, PA, FL. Next batch: VA, MD, UT, WA, CA and SAM. Relevance/extraction can run whenever slots permit. There is no requirement to run fourteen chats simultaneously.

Integration merge order: (1) core and transport; (2) adapters one at a time; (3) extraction/relevance; (4) operations; (5) packaging/CI/docs and end-to-end verification. Changes to the shared contract require integration approval and a version increment, with backward-compatible shims when practical; report the proposal instead of silently changing interfaces.

## Copy/paste prompts for individual chats

Prepend the shared instruction below to the selected assignment:

> Work in https://github.com/zldavidson/highway-env-serv.git at baseline commit `<BASELINE_SHA>`, in your own clone/worktree on the branch specified in docs/parallel-agent-plan.md. Read the plan, remaining-work spec and adapter-contract-v1.md. Implement only your owned files; leave shared-file changes as handoff proposals. Use no LLM calls in routine runtime code. Add meaningful offline tests and document live evidence or access limitations. Return your branch/commit or PR, test results and docs/handoffs/<task-id>.md. Do not deploy, send notifications, schedule jobs, or bypass access restrictions.

### Core

> Your task ID is core. Implement normalized opportunity/notice/attachment persistence, provenance, idempotent upserts, deadline/status uncertainty, amendment history, source health and checkpoints. Keep current PDF/FTS behavior compatible. Add a backed-up migration from the old prototype database without redownloading or re-extracting existing page text. Build adapter registry and pipeline/CLI wiring from the frozen contract using stubs until source adapters merge. Checkpoint advancement and record writes must be atomic. Test repeat runs, deadline extensions, incomplete runs, disappearing notices, failed attachment fetches and migration rollback. Do not edit transport, source adapters or package dependencies.

### Transport

> Your task ID is transport. Extract/harden the shared fetch client and generic crawler. Implement the fetch interface in adapter-contract-v1.md with scoped HTTPS redirects, robots enforcement, per-host pacing, bounded retry/Retry-After, conditional caching, explicit access diagnostics and injectable transports. Never log credential-bearing URLs. Distinguish attempts, successes, blocked resources and budget truncation. Handle HTML charset and HTTP status correctly. Test 304, 429, timeouts, redirect scope, robots errors, oversized responses and interruption/checkpoint integration interfaces. Investigate the FDOT Azure robots HTTP 400 without bypassing access policy; document supported handling and evidence. Do not change database schema or CLI.

### Pennsylvania

> Your task ID is pa. Build a PA eMarketplace adapter with PennDOT agency filtering, search form submission, full pagination, solicitation detail parsing, FileDownload attachments and amendment discovery. Assess ECMS separately and state exactly what is covered. Return all qualified notice attachments regardless of generic link label. Test empty search, multiple pages, duplicate notices, changed deadlines and attachment links. Reconcile a bounded live search against visible source counts. Do not edit shared source config or transport.

### Florida

> Your task ID is fl. Build FDOT maintenance opportunity discovery across districts 1–7 and Turnpike, including letting pages, notice PDFs and addenda. Separate maintenance from central construction and historical awards. Record the source/window/counts and district completeness. Use the shared fetch client; report attachment-host robots failures rather than bypassing them. Assess the state services procurement portal as an additional source, not an assumed replacement. Test district variation, future/past lettings, generic PDF labels, amendments and missing documents.

### Virginia

> Your task ID is va. Build eVA/VBO discovery for VDOT mowing, grounds, vegetation and environmental maintenance; retain public VDOT advertisement links as a distinct channel. Implement pagination/details/attachments and source-specific statuses/deadlines with provenance. Do not substitute historical eVA spending data for live solicitations. Test amendments, empty results, duplicates and unknown timezone. Perform a bounded live reconciliation or document access limits.

### Maryland

> Your task ID is md. Build eMMA public solicitation discovery filtered to MDOT/SHA and relevant maintenance services. Determine actual anonymous access, form/session requirements and pagination. Implement public details/attachments where accessible. If credentials are required, define an optional authorized session interface and deliver fixtures/tests with an authentication-required capability report; do not assume full coverage from a login page. Test session expiration, public/private attachments, amendments and empty vs failed results.

### Utah

> Your task ID is ut. Build U3P/Bonfire public discovery filtered to UDOT. Investigate documented APIs/exports first; if JavaScript is required, isolate a browser adapter and propose its dependency in your handoff. Implement pagination/details/attachments where accessible and record access restrictions. Test public/closed listings, amendments, dynamic page failure and credential-required documents. Do not use an unrelated consultant-only portal as full maintenance coverage.

### Washington

> Your task ID is wa. Build WSDOT public contracting discovery and assess WEBS goods/services as a separate channel. Record coverage gaps, authorized registration requirements, public details, attachments and amendments. Do not claim all Washington public agencies use WEBS. Test multiple channels, duplicate notices, listing truncation, inaccessible details and status uncertainty. Reconcile a bounded live public listing; provide an authorized-session interface only if needed.

### California

> Your task ID is ca. Build Cal eProcure Caltrans service solicitation discovery and retain public Caltrans procurement evidence. Verify current department filters and pagination rather than assuming historic instructions remain current. Handle 403/access failures explicitly; do not count bid results as open notices. Test detail/attachment parsing, amendments, unknown deadline timezone and empty/blocked results. Document a bounded live reconciliation or the exact access limitation.

### Federal SAM.gov

> Your task ID is sam. Implement the documented SAM.gov opportunities API against the frozen adapter contract. Read SAM_API_KEY only from environment, redact keys from requests/errors/evidence, validate date windows, paginate, enforce configured account quotas and fetch accessible descriptions/attachments. Combine NAICS 561730 and broader vegetation/environmental keyword searches; deduplicate by notice identity. Restrict known performance states to MD/VA/PA/FL/UT/WA/CA and retain unknown-location notices separately. Test pagination, throttling, missing key, amendments and credential redaction. Live verification may remain blocked without a key.

### Relevance

> Your task ID is relevance. Implement pure deterministic opportunity/page scoring returning category, score, rule matches and evidence. Prioritize vegetation/landscape scope and pay items, reduce environmental boilerplate and unrelated waste/consulting/construction matches. Optional restoration categories must be configurable. Use labeled positives/negatives and report precision/recall with sample size. No embeddings or LLM classifiers. Do not mutate persistence or CLI.

### Extraction

> Your task ID is extraction. Implement page extraction with optional local OCR capability detection, mixed-page quality flags, original/derivative separation and engine version metadata. Preserve original page numbering and original PDFs. OCR dependencies remain optional; propose installation/package changes in your handoff. Test text-only, image-only, mixed, rotated, malformed and encrypted PDFs and repeat extraction caching hooks. Do not edit store.py; expose the extraction function in the frozen contract for core integration.

### Operations

> Your task ID is operations. Implement single-writer locks, backup/restore helpers, source-health summaries and dry-run Windows Task Scheduler/cron templates. Do not install jobs or send messages. Design deduplicated notification event records without activating channels. Test interruption, lock contention, restore integrity, unchanged-run silence and source-failure visibility. Leave shared CLI/schema wiring as proposals for core/integration.

### Integration

> Your task ID is integration. Own the frozen contracts and shared files. Review branches/PRs in dependency order, reconcile interface differences, integrate approved dependency proposals and update docs/CI/lockfiles. Do not merge a source adapter as fully supported without offline tests plus live reconciliation or explicit access limitations. Run Windows/Linux checks and end-to-end repeated-run verification, confirm ignored runtime data/secrets, and publish a source capability matrix. Do not deploy or activate schedules/notifications. Coordinate through branch/PR handoffs; messaging other chats requires user authorization.
