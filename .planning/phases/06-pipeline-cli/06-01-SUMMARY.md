---
phase: 06-pipeline-cli
plan: 01
subsystem: orchestrator
tags: [orchestrator, pipeline, tdd, exports]
requires: [SCORE-01, SCORE-02, SCORE-04]
provides: [CLI-01]
affects: [src/checker/orchestrator.py, src/checker/__init__.py]
tech-stack:
  added: []
  patterns: [TDD, pipeline-orchestration, error-recovery, union-type-branching]
key-files:
  created:
    - src/checker/orchestrator.py
    - tests/test_orchestrator.py
  modified:
    - tests/conftest.py
    - src/checker/__init__.py
decisions:
  - "Stages schema/content only appended to stages_run when crawl guard passes (CrawlError skips them)"
  - "Fallback object construction for generate_report requires exists/found kwargs on RobotsResult/LlmsResult"
  - "run_pipeline returns dict (not ScoreReport directly) with errors, complete, and stages_run for CLI consumption"
metrics:
  duration: ""
  completed_date: ""
---

# Phase 06 Plan 01: Pipeline Orchestrator Summary

**One-liner:** Built the pipeline orchestrator that wires all five existing analysis phases into a single `run_pipeline()` function handling CrawlError branching and module failure recovery.

## Tasks Completed

| # | Type | Name | Commit | Files |
|---|------|------|--------|-------|
| 1 | TDD | run_pipeline() orchestrator with full test suite | a37374b (RED), ae02ac8 (GREEN) | `src/checker/orchestrator.py`, `tests/test_orchestrator.py`, `tests/conftest.py` |
| 2 | auto | Wire orchestrator into package exports | 6ef73fd | `src/checker/__init__.py` |

## Commits

- `a37374b`: `test(06-01): add failing orchestrator tests and conftest fixtures` — RED gate
- `ae02ac8`: `feat(06-01): implement run_pipeline() orchestrator` — GREEN gate
- `6ef73fd`: `feat(06-01): wire run_pipeline into package exports` — Task 2

## What Was Built

`src/checker/orchestrator.py` with `run_pipeline(url, timeout, verbose)` that:

1. **Stage sequencing:** Calls all five stages in order: crawl, access_signals, schema, content, score
2. **CrawlError branching:** When `fetch_url()` returns a `CrawlError`, skips schema and content (they need HTML) but still runs access signals and scoring for a partial report
3. **Error recovery:** Individual module exceptions (RuntimeError, ValueError) produce zero-score fallback objects and error messages — the pipeline never crashes
4. **Structured output:** Returns `dict` with `report` (ScoreReport), `errors` (list[str]), `complete` (bool), `stages_run` (list[str])
5. **Package export:** `run_pipeline` importable from `src.checker` via updated `__init__.py`

## Test Coverage

8 orchestrator tests covering:
- Full success pipeline (all 5 stages, complete=True)
- CrawlError handling (schema/content skipped, partial report)
- Access signals failure recovery (zero-score fallback)
- Schema analysis failure recovery
- Content analysis failure recovery
- Stages run order verification
- Fallback object compatibility with generate_report
- Multiple simultaneous module failures

Full suite: 101 tests pass, no regressions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 7 fallback objects missing required fields**
- **Found during:** Task 1 GREEN phase
- **Issue:** `RobotsResult(url=...)` and `LlmsResult(url=...)` omitted required positional args `exists` and `found`
- **Fix:** Updated Test 7 to pass `exists=False` and `found=False`, and changed the test to actually call `generate_report()` with fallback objects (matching the behavior spec, not just constructing ScoreReport directly)
- **Files modified:** `tests/test_orchestrator.py`
- **Commit:** `ae02ac8`

**2. [Rule 3 - Blocking] scorer.py (Phase 5) not present on worktree**
- **Found during:** Execution start
- **Issue:** The worktree branch was based on Phase 4 commits; Phase 5 scorer code was on `phase/05-scorer-report` branch only
- **Fix:** Merged `phase/05-scorer-report` into the worktree branch to bring in `src/checker/scorer.py`, `ScoreReport` contract, and Phase 5 tests
- **Files affected:** 22 files merged (scorer.py, contracts.py, __init__.py updates, test_scorer.py, Phase 5-6 plan/research docs)

## Verification

- `pytest tests/test_orchestrator.py -x -v` — 8 tests pass
- `pytest tests/ -x -q` — 101 tests pass (no regressions)
- `grep -c "def run_pipeline" src/checker/orchestrator.py` — 1
- `grep -c "isinstance.*CrawlError" src/checker/orchestrator.py` — 3
- `grep -c "def test_" tests/test_orchestrator.py` — 8
- `python -c "from src.checker import run_pipeline; assert callable(run_pipeline)"` — OK
- All acceptance criteria met

## Self-Check: PASSED

- `src/checker/orchestrator.py` — FOUND
- `tests/test_orchestrator.py` — FOUND
- Commit `a37374b` — FOUND
- Commit `ae02ac8` — FOUND
- Commit `6ef73fd` — FOUND
