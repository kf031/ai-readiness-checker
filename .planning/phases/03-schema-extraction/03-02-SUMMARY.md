---
phase: 03-schema-extraction
plan: 02
type: execute
subsystem: schema
tags: [schema-extraction, type-detection, weighted-scoring, extruct]
dependencies:
  provides: [schema_analyzer, SchemaAnalysis, analyze_schema, extract_structured_data, collect_schema_types, compute_schema_score]
  requires: [SchemaAnalysis, FetchResult, extruct, Phase 3 fixtures]
  affects: [Phase 5 scorer (schema component, 30% weight)]
tech-stack:
  added: []
  patterns: [tdd, uniform-api, recursive-type-collection, presence-based-scoring]
key-files:
  created:
    - src/checker/schema_analyzer.py (266 lines, 5 functions, 2 constants)
  modified:
    - src/checker/__init__.py (Phase 3 exports + docstring)
    - tests/test_schema.py (replaced 16 stubs with 19 real tests)
decisions:
  - "normalize_type_name applies .title() only to all-lowercase strings to preserve PascalCase (e.g., FAQPage, BreadcrumbList)"
  - "extract_structured_data normalizes output to always include all 4 format keys (extruct omits json-ld when all blocks malformed)"
  - "Scoring is per-concrete-type (sum of weights), not per-category"
metrics:
  duration: ~30 minutes
  tasks: 2
  tests: 59 passed (40 Phase 1+2, 19 Phase 3)
  completed_date: 2026-05-03
---

# Phase 3 Plan 2: Schema Analyzer Summary

Implemented `src/checker/schema_analyzer.py` with structured data extraction across 4 formats (JSON-LD, microdata, OpenGraph, RDFa) via extruct, type normalization and collection with @graph recursion, and weighted 0.0-1.0 scoring for 9 concrete schema.org types mapping to 6 high-value categories.

**One-liner:** Schema extraction and weighted scoring pipeline consuming FetchResult.html and returning SchemaAnalysis with detected types, per-type metadata, and FAANG-weighted score.

## Completed Tasks

### Task 1 (TDD): Create schema_analyzer.py

**RED phase** (commit `4013621`): Replaced 16 `pytest.skip` stubs in `tests/test_schema.py` with 19 real test implementations covering extraction, type detection, scoring, and structural integrity.

**GREEN phase** (commit `6c9de7e`): Created `src/checker/schema_analyzer.py` with:

| Function/Constant | Purpose |
|---|---|
| `TARGET_TYPES` | Weight dict for 9 concrete schema.org types (sum = 1.0) |
| `TYPE_CATEGORY` | Maps 9 types to 6 category groups |
| `extract_structured_data()` | Wraps extruct with `uniform=True`, `errors="log"`, normalizes output keys |
| `normalize_type_name()` | Converts URIs to short names, title-cases only lowercase strings |
| `collect_schema_types()` | Recursive traversal across all 4 formats, handles @graph and RDFa lists |
| `compute_schema_score()` | Sums per-concrete-type weights with `min(score, 1.0)` guard |
| `analyze_schema()` | Single public entry point returning populated `SchemaAnalysis` |

### Task 2: Wire Phase 3 exports

Commit `68c0342`: Updated `src/checker/__init__.py`:
- Added Phase 3 to module docstring
- Imported `SchemaAnalysis` from contracts and `analyze_schema` from schema_analyzer
- Extended `__all__` list with both exports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `.title()` corrupts PascalCase type names**
- **Found during:** Task 1 GREEN phase
- **Issue:** `normalize_type_name` applied `.title()` unconditionally, turning `"FAQPage"` into `"Faqpage"` and `"BreadcrumbList"` into `"Breadcrumblist"`
- **Fix:** Only apply `.title()` when `type_str.islower()` is True (OpenGraph lowercase convention). Already-PascalCase strings pass through unmodified.
- **Files modified:** `src/checker/schema_analyzer.py` (normalize_type_name function)
- **Also fixed in:** `tests/test_schema.py` (matching test expectations)

**2. [Rule 2 - Missing critical functionality] extruct output missing expected format keys**
- **Found during:** Task 1 GREEN phase
- **Issue:** When extruct's `errors="log"` encounters malformed JSON-LD, the entire `json-ld` key is absent from the output dict. Downstream code (`collect_schema_types`, `analyze_schema`) expects all 4 keys to be present.
- **Fix:** Added key normalization loop after extruct call — `result.setdefault(key, [])` for all 4 format keys. Ensures consistent output shape regardless of extruct's error behavior.
- **Files modified:** `src/checker/schema_analyzer.py` (extract_structured_data function)

**3. [Rule 1 - Bug] Floating-point precision in all-6-category score test**
- **Found during:** Final full test suite run
- **Issue:** `0.25 + 0.25 + 0.08 + 0.10 + 0.05 + 0.075` = `0.8049999999999999` not exactly `0.805` due to IEEE 754 double precision
- **Fix:** Changed strict equality to `pytest.approx(0.805)` in `test_score_all_categories`
- **Files modified:** `tests/test_schema.py`

## Verification

- **Test suite:** 59/59 passing (40 Phase 1+2 + 19 Phase 3)
- **Plan verification commands:** All SCHEMA-01, SCHEMA-02, SCHEMA-03 checks passed
- **Acceptance criteria:** All grep checks for function presence, constant definitions, syntaxes list, forbidden patterns, and import verification passed
- **Threat mitigations:** T-03-01 (malformed JSON-LD DoS) mitigated via `errors="log"` + key normalization; T-03-02 through T-03-04 accepted per threat register

## Self-Check: PASSED

- [x] `src/checker/schema_analyzer.py` exists (266 lines)
- [x] `src/checker/__init__.py` has Phase 3 exports
- [x] `tests/test_schema.py` has 19 real tests
- [x] Commit `4013621` exists (test RED)
- [x] Commit `6c9de7e` exists (feat GREEN)
- [x] Commit `68c0342` exists (feat wiring)
