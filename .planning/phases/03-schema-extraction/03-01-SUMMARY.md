---
phase: 03-schema-extraction
plan: 01
subsystem: checker
tags: [dataclass, contracts, test-scaffold, fixtures, schema-extraction]
depends_on: []
requires: []
provides: [SchemaAnalysis dataclass, schema test infrastructure]
affects: [src/checker/contracts.py, tests/conftest.py, tests/test_schema.py]
tech-stack:
  added: []
  patterns: [field(default_factory=...) for mutable dataclass defaults, SCREAMING_SNAKE_CASE for HTML string fixtures, pytest.skip() for stub tests]
key-files:
  created: [tests/test_schema.py]
  modified: [src/checker/contracts.py, tests/conftest.py]
decisions:
  - "SchemaAnalysis uses field(default_factory=dict/set) for all mutable fields, matching existing Phase 1-2 patterns"
  - "16 test stubs use pytest.skip() referencing Plan 03-02, matching the Phase 2 stub pattern"
  - "Fixtures use SCHEMA_ prefix, following existing ROBOTS_TXT_ and LLMS_TXT_ naming conventions"
metrics:
  duration_seconds: 0
  completed_date: 2026-05-03
  tasks_total: 2
  tasks_completed: 2
---

# Phase 3 Plan 1: Schema Data Contract and Test Scaffold Summary

## One-Liner

SchemaAnalysis dataclass with 6 fields and mutable-default pattern added to contracts.py, 8 structured-data HTML fixtures appended to conftest.py, and test_schema.py created with 16 pytest.skip() stubs covering SCHEMA-01/02/03 behaviors.

## Tasks Executed

### Task 1: Add SchemaAnalysis dataclass to contracts.py

- Inserted `SchemaAnalysis` dataclass between `LlmsResult` and the v2 TODO comment
- 6 fields: `url`, `raw`, `detected_types`, `type_details`, `score`, `fetched_at`
- All mutable fields use `field(default_factory=...)` — no raw `{}` or `set()`
- Updated module docstring from `"(future) SchemaAnalysis"` to `"SchemaAnalysis"`
- All existing dataclasses and imports untouched
- **Commit:** `4d9958f`

### Task 2: Add 8 schema HTML fixtures and 16 test stubs

- Added 8 `SCHEMA_*` HTML string constants to `tests/conftest.py`
- Fixtures cover: JSON-LD Product, microdata FAQPage, @graph multi-type, RDFa BreadcrumbList, OpenGraph product, multi-format page, malformed JSON-LD + valid microdata, empty HTML
- Created `tests/test_schema.py` with 16 `pytest.skip("implement in Plan 03-02")` stubs
- Stubs organized by requirement: 3 for SCHEMA-01 (extraction), 9 for SCHEMA-02 (type detection), 4 for SCHEMA-03 (scoring)
- **Commit:** `70e4267`

## Verification Results

- SchemaAnalysis imports, instantiates, and defaults score=0.0, raw={}, detected_types=set(), type_details={}
- All 8 SCHEMA_ fixtures importable from conftest.py
- All 16 test stubs recognized by pytest (16 skipped)
- All 40 existing Phase 1 + Phase 2 tests continue to pass (40 passed, 16 skipped)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

All 16 test functions in `tests/test_schema.py` are intentional stubs that use `pytest.skip("implement in Plan 03-02")`. These are the design target for Plan 03-02 which will implement `src/checker/schema_analyzer.py` and replace each stub with a real implementation. This is an intentional test-scaffold pattern, not a gap.

## Threat Flags

None — this plan adds only a dataclass definition and test stubs. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The threat mitigations referenced in the plan's threat model (T-03-01: `errors="log"`) will be implemented in Plan 03-02 when `schema_analyzer.py` is created.

## Self-Check

PASSED — all created/modified files exist and both commits are verified in git log.
