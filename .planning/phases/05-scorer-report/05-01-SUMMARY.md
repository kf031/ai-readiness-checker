---
phase: 05-scorer-report
plan: 01
type: execute
subsystem: scorer
tags: ["scoring", "report", "composition", "dataclass"]
requires: ["Phase 2 (robots_txt, llms_txt modules)", "Phase 3 (schema)", "Phase 4 (content)"]
provides: ["ScoreReport dataclass", "weighted overall score", "letter grade mapping", "structured report generation"]
affects: ["Phase 6 (CLI orchestration)", "Phase 7 (Streamlit dashboard)"]
tech-stack:
  added: []
  patterns: ["Composition layer importing existing scoring functions", "Score validation with NaN/Inf guards", "Dataclass defaults with UTC timestamp factory"]
key-files:
  created:
    - src/checker/scorer.py
    - tests/test_scorer.py
  modified:
    - src/checker/contracts.py
    - src/checker/__init__.py
decisions:
  - "Robots score range [0.01, 0.99] accepted as-is — max overall score is 99.8, not 100.0"
  - "Recommendations list is always empty (filled in Plan 02)"
  - "Empty bots list (fetch error) returns 0.5 baseline via compute_bot_score"
metrics:
  duration: "~4 minutes"
  completed_date: "2026-05-04"
  task_count: 2
  test_count: 13
  file_count: 4
---

# Phase 5 Plan 01: Core Scoring + Report Data Contract

**One-liner:** Weighted AI-readiness scoring composition layer that imports existing module scoring functions to produce a 0-100 overall score with A-F letter grade and structured ScoreReport.

## Tasks Completed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Add ScoreReport dataclass + test scaffold | auto | `bc43f06` | Complete |
| 2 | Implement scorer + tests (TDD RED/GREEN) | auto | `dc51718` | Complete |

### Task 1: ScoreReport dataclass + test scaffold (`bc43f06`)

Added `ScoreReport` dataclass to `src/checker/contracts.py` with 6 fields:
- `url`: str
- `overall_score`: float (default 0.0)
- `grade`: str (default "F")
- `module_breakdown`: dict with score/weight/weighted per module
- `recommendations`: list (default [], filled in Plan 02)
- `timestamp`: datetime (auto-set to UTC on construction)

Created `tests/test_scorer.py` with 13 test stubs (pass body), all discoverable by pytest.

### Task 2: Scorer implementation (`dc51718`)

**RED (`4e12e27`):** Filled in all 13 test stubs with assertions. Tests failed with `ModuleNotFoundError` — expected.

**GREEN (`dc51718`):** Created `src/checker/scorer.py` with:

- **`MODULE_WEIGHTS`**: robots=0.20, llms_txt=0.15, schema=0.30, content=0.35
- **`compute_overall_score(scores)`**: Weighted sum * 100, rounded to 1 decimal (SCORE-01)
- **`letter_grade(overall_score)`**: 85=A, 70=B, 55=C, 40=D, 0=F (SCORE-02)
- **`generate_report(url, robots_result, llms_result, schema_analysis, content_analysis)`**: Assembles ScoreReport (SCORE-04)
- **`_validate_score(value, label)`**: Guards against NaN, Inf, out-of-range inputs (T-05-01, T-05-02)
- **`_extract_scores(...)`**: Imports `compute_bot_score` and `compute_llms_score` rather than reimplementing

Updated `src/checker/__init__.py` to export `ScoreReport` and `generate_report`.

## Verification Results

```
13 passed in 1.35s

tests/test_scorer.py::test_weighted_score_calculation PASSED
tests/test_scorer.py::test_overall_score_all_zeros PASSED
tests/test_scorer.py::test_overall_score_all_max PASSED
tests/test_scorer.py::test_grade_boundary_A_low PASSED
tests/test_scorer.py::test_grade_boundary_AB_edges PASSED
tests/test_scorer.py::test_grade_all_boundaries PASSED
tests/test_scorer.py::test_report_has_required_keys PASSED
tests/test_scorer.py::test_report_module_breakdown PASSED
tests/test_scorer.py::test_report_timestamp_is_utc PASSED
tests/test_scorer.py::test_report_json_serializable PASSED
tests/test_scorer.py::test_robots_fetch_error_handling PASSED
tests/test_scorer.py::test_empty_bots_score PASSED
tests/test_scorer.py::test_all_blocked_score PASSED
```

Manual verification output: `compute_overall_score({robots:0.85, llms:0.3, schema:0.7, content:0.6}) = 63.5, grade C` — matches expected calculation.

All 4 acceptance criteria met:
1. `compute_overall_score` correctly applies weights and returns 0-100 to 1 decimal
2. `letter_grade` correctly maps all boundary scores (85.0=A, 84.9=B, 70.0=B, etc.)
3. `generate_report` returns proper ScoreReport with all 6 fields, 4-module breakdown, UTC timestamp
4. Robots score range [0.01, 0.99] flows through → max overall is 99.8
5. NaN/Inf/out-of-range scores guarded with validation → coerced to 0.0
6. All 13 tests pass

## Deviations from Plan

None — plan executed exactly as written. All code, behavior, and test assertions matched the plan specification.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `recommendations: list = field(default_factory=list)` | `src/checker/contracts.py` | ScoreReport field | Filled in Plan 02 (recommendation generation) |
| `recommendations=[]` in generate_report | `src/checker/scorer.py` | line 154 | Filled in Plan 02 — currently always empty |

Both stubs are intentional per the plan specification: "Empty list when recommendations are not yet implemented (Plan 02)."

## Threat Flags

None — all implementation threats covered by the plan's threat model:
- T-05-01 (NaN/Inf DoS): Mitigated with `_validate_score` + `math.isfinite()` guard
- T-05-02 (Score overflow tampering): Mitigated with clamping in `_validate_score`
- T-05-03 (Information disclosure): Accepted — recommendations list is empty, no user-controlled strings flow into output

## Requirements Satisfied

- **SCORE-01**: Weighted overall score with correct weights (20/15/30/35)
- **SCORE-02**: A-F letter grade mapping with exact boundary handling
- **SCORE-04**: Structured ScoreReport with all required fields (url, overall_score, grade, module_breakdown, recommendations, timestamp)

## Self-Check: PASSED

- `src/checker/scorer.py` — FOUND
- `tests/test_scorer.py` — FOUND
- Commit `bc43f06` — FOUND (feat: ScoreReport + test scaffold)
- Commit `4e12e27` — FOUND (test: RED phase)
- Commit `dc51718` — FOUND (feat: GREEN phase — scorer implementation)
