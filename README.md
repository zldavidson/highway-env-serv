# Highway Contracts

A repeatable public procurement PDF scraper and local search index. Routine runs use no model tokens, paid APIs, or vector database.

## Install and run

Python 3.11+ with SQLite FTS5 support:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m highway_contracts crawl --source fl-fdot --max-requests 40
.\.venv\Scripts\python.exe -m highway_contracts ingest seed_pdfs.json
.\.venv\Scripts\python.exe -m highway_contracts search 'environment* OR mowing OR vegetation' --state PA --csv output/results.csv
.\.venv\Scripts\python.exe -m highway_contracts stats
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run from the repository root. Global --data-dir must precede the command. Repeat --source to select multiple sources. Without --source the configured enabled sources run.

## Pipeline

Configured start pages -> bounded relevant HTML links -> public PDF downloads -> SHA-256 originals -> page text -> SQLite FTS5 -> JSON results / optional CSV.

The crawler respects robots.txt, exact HTTPS host allowlists, crawl delays, redirect scope, maximum depth and request budgets. Downloads have a 50 MB cap. Transient failures are retried with bounded backoff. Conditional requests use ETag/Last-Modified when available. Unchanged indexed PDFs skip extraction; changed PDFs retain history while searches use the latest observed version per URL/source.

Run reports record errors, sources yielding no PDFs, and truncated queues. Exit code 1 means errors or a source requiring adapter review. Always inspect truncation even if exit code is 0. Runs are single-process; do not run concurrent writers against one data directory.

## Current coverage

The generic HTML crawler is implemented. State configurations are provisional seeds, not certified complete adapters.

| Source | Remaining source-specific work |
|---|---|
| PA eMarketplace | Search forms, pagination and solicitation metadata |
| FDOT | Complete district/Turnpike traversal and metadata; Azure PDF host robots check currently returns HTTP 400 and is reported as blocked |
| VDOT | eVA live goods/services adapter beyond public advertisements |
| WSDOT | WEBS adapter beyond public contracting pages |
| Caltrans | Cal eProcure adapter beyond public procurement pages |
| Maryland eMMA | Session/public search adapter; disabled by default |
| Utah U3P | JavaScript listing adapter; disabled by default |

Live FDOT smoke check fetched public HTML and discovered an attachment, but the attachment host robots check failed. This is reported explicitly rather than counted as a successful PDF collection. Full seven-state collection is not complete.

## Data

Source adapters can use the dataclasses in `highway_contracts.models`: `Evidence`,
`Attachment`, `Opportunity`, `Diagnostic`, and `DiscoveryBatch`. Their `to_dict()`
and `to_json()` methods serialize nested records with string enum values. Timestamps
are ISO 8601; ambiguous deadlines stay in `deadline_raw` with `deadline_at` and
`deadline_timezone` null. Adapters must retain known offsets and redact credentials,
cookies, and sensitive response fields before creating evidence.

Use authoritative notice IDs. When unavailable, `detail_url_identity()` returns a
normalized detail URL and a diagnostic that must be included in the batch. Titles
are never identity keys. Diagnostic codes distinguish `authentication_required`,
`blocked`, `parser_error`, `transport_error`, `verified_empty`, `truncated`, and
`unsupported`. `DiscoveryBatch.verified_empty` requires a complete empty batch
without blocking or parser diagnostics. The existing PDF crawler report remains
separate; it does not yet produce opportunity discovery batches.

- data/pdfs/: original content-addressed PDFs.
- data/crawler.sqlite: cached responses, document versions, extracted pages and current-version pointers.
- data/runs/: timestamped JSON reports.
- output/results.csv: optional search export.

Generated data and credentials are ignored by Git. Existing prototype data/contracts.sqlite remains intact and separate from the new schema. Re-ingest seed_pdfs.json to populate the new database. The manifest contains historical/reference samples, not verified open bids.

Search uses SQLite FTS5 syntax: environment* matches prefixes; OR broadens queries; quote phrases inside the query for adjacency. Search results include state, source, PDF URL, local path and page number. Low-text pages are flagged for OCR review, but OCR is not yet implemented. Search hits are passages, not qualified leads. Environmental boilerplate can produce unrelated matches.

See [remaining-work spec](docs/remaining-work-spec.md) for adapters, deadlines/status, OCR, relevance, operations, scheduling, notifications and UI acceptance criteria.
