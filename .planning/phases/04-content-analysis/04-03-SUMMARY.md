---
phase: 04-content-analysis
plan: 03
subsystem: content-analysis
tags: [headings, QA-density, combined-score, orchestrator, spaCy-fallback]
requires:
  - phase: 04-02
    provides: content_analyzer.py with readability, text-ratio, and entity functions + 7 working tests
provides:
  - analyze_headings(soup) — H1 uniqueness, H2/H3 hierarchy, heading descriptiveness (>3 words)
  - score_headings(analysis) — 0.0-1.0 from H1, hierarchy, and descriptiveness sub-scores
  - _is_question(text) — question detection via ? ending or question-word start (no regex, T-4-05)
  - analyze_qa_density(text, soup) — sentence-level QA pairs + heading-level question detection
  - score_qa_density(analysis) — QA pair ratio normalized to 0.0-1.0 with 0.10 ceiling
  - compute_combined_score(...) — weighted aggregation of 5 sub-signals with equal 0.2 weight
  - analyze_content(fetch_result) — full pipeline orchestrator, returns ContentAnalysis
  - 14 green content tests (all CONT-01 through CONT-06 covered)
  - analyze_content exported from src.checker public API
affects: [05-scoring-report]

tech-stack:
  added: []
  patterns:
    - "analyze_headings: simple DOM traversal (soup.find_all) on Phase 1 pre-parsed tree"
    - "_is_question: string-only operations (endswith, split) — no regex, no ReDoS risk (T-4-05)"
    - "analyze_qa_density: reuse _get_nlp() lazy spaCy loader, fall back to period-split sentence count"
    - "compute_combined_score: clamp with min(max(x, 0.0), 1.0) per T-4-06"
    - "analyze_content: guard clause for empty text returns all-zero ContentAnalysis"
    - "spaCy missing: entity_score=0.0, qa_density_score=0.0, no crash"

key-files:
  created: []
  modified:
    - src/checker/content_analyzer.py (550 lines, 13 functions)
    - src/checker/__init__.py (analyze_content export + __all__ entry)
    - tests/test_content.py (14 tests, 0 stubs)

key-decisions:
  - "Equal weighting (0.2) for all 5 sub-signals in compute_combined_score — simplest defensible default"
  - "Heading question detection weighted at 0.5 to avoid double-counting bias against sentence-level questions"
  - "H1 scoring: 1.0 for exactly 1, 0.5 for 0, 0.0 for >1 (per RESEARCH.md formula)"
  - "QA density ceiling at 0.10: a page where 10%+ of sentence pairs are QA scores maximum 1.0"
  - "analyze_content orchestrator pattern matches analyze_schema in schema_analyzer.py — single public entry point"

requirements-completed: [CONT-04, CONT-05, CONT-06]

metrics:
  duration: 7min
  completed: 2026-05-03
---

# Phase 4 Plan 03: Content Analyzer Completion Summary

**Final integration: heading structure analysis, Q&A density scoring, combined score aggregator, and analyze_content() orchestrator -- all 14 content tests green, Phase 4 module fully exportable**

## Performance

- **Duration:** ~7min
- **Started:** 2026-05-03T14:29:26Z
- **Completed:** 2026-05-03T14:36:28Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- 7 new functions added to content_analyzer.py: analyze_headings, score_headings, _is_question, analyze_qa_density, score_qa_density, compute_combined_score, analyze_content
- Heading analysis covers H1 uniqueness (1.0/0.5/0.0 scoring), H2/H3 hierarchy validation, and heading descriptiveness (>3 words)
- Q&A density detects both sentence-level questions (via _is_question) and heading-level questions, with heading questions weighted at 0.5
- Combined score aggregates all 5 sub-signals with equal 0.2 weight, result clamped to [0.0, 1.0] per T-4-06
- analyze_content(fetch_result) orchestrates the full pipeline: text extraction -> readability -> ratio -> entities -> headings -> QA -> combined
- Empty page guard clause returns all-zero ContentAnalysis without crashing
- spaCy model missing falls back gracefully: entity_score=0.0, qa_density_score=0.0
- All 4 remaining test stubs replaced with real assertions
- analyze_content exported from src.checker and added to __all__
- Full test suite: 73 passed (14 content + 59 from Phases 1-3), 0 failures

## Task Commits

1. **Task 1: Add heading analysis and QA density functions** - `0328354` (feat)
2. **Task 2: Implement tests and wire package exports** - `8c7ee8f` (test)

## Files Modified

- `src/checker/content_analyzer.py` — Added 357 lines: analyze_headings, score_headings, _is_question, QUESTION_WORDS, analyze_qa_density, score_qa_density, SUB_SIGNAL_WEIGHTS, compute_combined_score, analyze_content. Total: 550 lines, 13 functions.
- `src/checker/__init__.py` — Added `from src.checker.content_analyzer import analyze_content` import and `"analyze_content"` to `__all__`
- `tests/test_content.py` — Replaced 4 assert-False stubs with 7 real tests: test_heading_structure, test_heading_structure_no_headings, test_qa_density, test_qa_density_empty_text, test_combined_score, test_empty_page_integration, test_spacy_model_missing

## Decisions Made

- Equal weighting (0.2 each) for all 5 sub-signals: simplest defensible default since no requirements specify per-signal weights
- Heading question detection weighted at 0.5 to prevent double-counting bias (same question appearing both as heading and in body text)
- QA density ceiling at 0.10 ratio: research-backed threshold where QA-rich pages max out
- _is_question uses only string operations (endswith, split) -- no regex, directly mitigating T-4-05 ReDoS threat
- compute_combined_score clamps output regardless of input, defending against T-4-06 tampering

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Merged main branch to bring in Phase 1-4 source code**
- **Found during:** Pre-execution setup
- **Issue:** Worktree branch (worktree-agent-adb0e75939edce6dd) was created from early commit e67a9d4 predating all source code. No src/, tests/, or pyproject.toml existed.
- **Fix:** Ran `git merge main` (fast-forward) to bring in all Phase 1-4 files (53 files, 13714 insertions)
- **Verification:** All 73 tests pass including existing 7 content tests
- **Commit:** N/A (fast-forward merge, identical to Plan 04-02 worktree initialization pattern)

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Standard worktree initialization pattern. No scope creep.

## Issues Encountered

- Worktree initially empty (same `worktree-agent-*` initialization quirk from 04-01 and 04-02); resolved by merging main

## User Setup Required

None -- all dependencies (textstat 0.7.13, spaCy 3.8.14, en_core_web_sm model) were installed in Plan 04-01.

## Known Stubs

None -- all 4 previous test stubs are now implemented. All 14 content tests pass green.

## Phase 4 Completion Status

All 6 content analysis requirements (CONT-01 through CONT-06) are now implemented with passing tests:

| Requirement | Signal | Status |
|------------|--------|--------|
| CONT-01 | Readability (Flesch + Fog) | Pass |
| CONT-02 | Content-to-HTML ratio | Pass |
| CONT-03 | Named entity extraction | Pass |
| CONT-04 | Heading structure | Pass |
| CONT-05 | Q&A density | Pass |
| CONT-06 | Combined score | Pass |

The content_analyzer module is complete with a single public entry point (`analyze_content`) that Phase 5 (scorer/report) can consume for the content component at 35% weight.

---
## Self-Check: PASSED

- `src/checker/content_analyzer.py` — FOUND (550 lines, 13 functions)
- `src/checker/__init__.py` — FOUND (analyze_content exported)
- `tests/test_content.py` — FOUND (14 tests, all pass)
- Commit `0328354` — FOUND
- Commit `8c7ee8f` — FOUND
- All 73 tests pass (14 content + 59 prior phases)

---
*Phase: 04-content-analysis* *Completed: 2026-05-03*
