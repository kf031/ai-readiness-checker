---
phase: 07-streamlit-dashboard
plan: 01
subsystem: orchestrator
tags: [orchestrator, contracts, test-fixtures, dashboard-prep]
requires: []
provides: [raw-module-objects-in-pipeline-result, dashboard-test-fixtures]
affects: [src/checker/orchestrator.py, tests/test_orchestrator.py, tests/conftest.py]
tech-stack:
  added: []
  patterns: [pipeline-result-extension, composable-test-fixtures]
key-files:
  created: []
  modified:
    - src/checker/orchestrator.py
    - tests/test_orchestrator.py
    - tests/conftest.py
decisions:
  - "Surfaced 4 raw module objects in run_pipeline() return dict using or-fallback pattern for robustness"
  - "Added isinstance type checks in both success and crawl-error test paths for defense-in-depth"
  - "Dashboard fixtures composable with existing module result fixtures via pytest dependency injection"
metrics:
  duration: 2m46s
  completed_date: "2026-05-13"
---

# Phase 7 Plan 1: Orchestrator Return Dict Extension Summary

Extended `run_pipeline()` return dict from 4 keys to 8 keys by surfacing raw module result objects (`RobotsResult`, `LlmsResult`, `SchemaAnalysis`, `ContentAnalysis`) that already existed in the orchestrator's local scope. Updated all 5+ orchestrator tests with new key assertions and isinstance type checks. Added reusable dashboard test fixtures (`sample_score_report`, `mock_pipeline_result`) to conftest.

## One-Liner

Orchestrator return dict now exposes 4 raw module objects alongside the ScoreReport, enabling dashboard expanders to render bot-by-bot tables, llms.txt validation errors, schema type details, and content sub-signal breakdowns.

## Deviations from Plan

None - plan executed exactly as written.

## Completed Tasks

| # | Name | Type | Commit | Files |
|---|------|------|--------|-------|
| 1 | Add raw module objects to orchestrator return dict | auto | c449f5d | src/checker/orchestrator.py |
| 2 | Update orchestrator test assertions for 8-key return dict | auto | 52a972b | tests/test_orchestrator.py |
| 3 | Add dashboard test fixtures to conftest.py | auto | 3355166 | tests/conftest.py |

## Known Stubs

None. This plan modifies data flow and test infrastructure only. No UI code, no placeholder values, no unwired components.

## Threat Flags

None. The 4 new keys expose data that was already in memory and was already passed to `generate_report()` at lines 98-102 of the same function. No new trust boundaries, network endpoints, auth paths, or schema changes introduced.

## Self-Check

- [PASS] `src/checker/orchestrator.py` contains all 4 new keys in return dict (verified via grep and `inspect.getsource`)
- [PASS] All 8 orchestrator tests pass (`pytest tests/test_orchestrator.py -x -v`)
- [PASS] Both dashboard fixtures discoverable by pytest (`--fixtures` shows `sample_score_report` and `mock_pipeline_result`)
- [PASS] Commits exist: c449f5d (task 1), 52a972b (task 2), 3355166 (task 3)
- [PASS] Backward-compatible: all 4 original keys preserved, CLI access patterns unchanged
