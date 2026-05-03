---
phase: 05-scorer-report
plan: 02
subsystem: scoring
tags: [recommendations, priority-sorting, quality-gates, dataclasses, pytest]

# Dependency graph
requires:
  - phase: 05-scorer-report/01
    provides: ScoreReport dataclass, core scoring (compute_overall_score, letter_grade, generate_report), 13 existing tests
  - phase: 02-access-signals
    provides: RobotsResult, BotStatus, compute_bot_score
  - phase: 02-access-signals
    provides: LlmsResult, compute_llms_score
  - phase: 03-schema-extraction
    provides: SchemaAnalysis
  - phase: 04-content-analysis
    provides: ContentAnalysis
provides:
  - Four per-module recommendation generators (_robot_recommendations, _llms_recommendations, _schema_recommendations, _content_recommendations)
  - generate_recommendations orchestrator with priority sorting (HIGH > MEDIUM > LOW)
  - generate_report wired to include prioritized recommendations in ScoreReport
  - 7 new recommendation tests (total 20)
affects: [06-pipeline-cli, 07-streamlit-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Template-based recommendation generation: each module function inspects typed result dataclasses and produces dict[priority, module, message]"
    - "Quality gate thresholds: schema skips recs at >=0.7, content skips recs at combined_score >=0.6"
    - "Python stable sort for priority ordering via sorted(key=lambda r: PRIORITY_ORDER.get(r[priority], 99))"

key-files:
  created: []
  modified:
    - src/checker/scorer.py - added recommendation generators, threshold constants, generate_recommendations, wired into generate_report
    - tests/test_scorer.py - added 7 recommendation tests (tests 14-20), total 20

key-decisions:
  - "Used list.sort-style key function with PRIORITY_ORDER dict for stable priority sorting"
  - "Content sub-score threshold set uniformly at 0.3 per RESEARCH.md Pitfall 4 guidance"
  - "fetch_error strings included in recommendation messages (controlled error_type values from upstream modules)"

patterns-established:
  - "Per-module recommendation generators return list[dict], empty list means no issues"
  - "Quality gates: perfect modules produce no noise (empty list bypass)"
  - "generate_recommendations concatenates all module recs and sorts once"

requirements-completed: [SCORE-03, SCORE-04]

# Metrics
duration: 4min
completed: 2026-05-04
---

# Phase 5 Plan 2: Recommendation Generation Summary

**Per-module recommendation generators with quality gates, priority sorting, and full integration into ScoreReport via generate_report**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-04T00:55:01+08:00
- **Completed:** 2026-05-04T00:58:50+08:00
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Four per-module recommendation generators inspect typed result dataclasses and produce specific, actionable plain-English messages
- Quality gates prevent noise: schema score >= 0.7 skips recs, content combined_score >= 0.6 skips recs
- Priority sorting ensures HIGH issues appear before MEDIUM before LOW in the report
- generate_report now produces populated recommendations (was empty list in Plan 01)
- 20 tests total (13 from Plan 01 + 7 new recommendation tests), all passing

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing recommendation tests** - `7beb0d0` (test)
2. **Task 1 (GREEN): Implement recommendation generators and wire into generate_report** - `7b64053` (feat)

_Note: TDD cycle completed — RED tests first, then GREEN implementation._

## Files Modified
- `src/checker/scorer.py` - Added 4 recommendation generator functions, threshold/configuration constants, `generate_recommendations` orchestrator, wired into `generate_report`
- `tests/test_scorer.py` - Added 7 new test functions (14-20) covering all recommendation scenarios

## Decisions Made
None significant — followed the plan's exact implementation specification, including the RESEARCH.md guidance for quality gate thresholds and message templates.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture for content subscores triggered all 5 recommendations instead of 2**
- **Found during:** Task 1 Step 4 (GREEN verification)
- **Issue:** test_recommendation_low_content_subscores created ContentAnalysis with only combined_score, readability_score, and heading_score set. The remaining sub-scores (text_ratio, entity_score, qa_density_score) defaulted to 0.0, which is below the 0.3 threshold, causing all 5 recommendations to fire.
- **Fix:** Set text_ratio=0.8, entity_score=0.8, qa_density_score=0.8 in the test fixture to isolate the two subscores being tested (readability=0.1, heading=0.1).
- **Files modified:** tests/test_scorer.py
- **Verification:** Test now passes with exactly 2 recommendations (readability + heading).
- **Committed in:** `7b64053` (GREEN commit)

**2. [Rule 1 - Bug] Multi-line sorted() call failed grep acceptance criteria**
- **Found during:** Task 1 Step 5 (REFACTOR check / acceptance criteria verification)
- **Issue:** The `sorted()` call was split across 3 lines, causing `grep -c "sorted.*PRIORITY_ORDER"` to return 0 instead of the expected 1. The plan's acceptance criteria used a single-line grep pattern.
- **Fix:** Inlined the sorted() call to a single line: `all_recs = sorted(all_recs, key=lambda r: PRIORITY_ORDER.get(r["priority"], 99))`
- **Files modified:** src/checker/scorer.py
- **Verification:** grep returns 1, all tests still pass.
- **Committed in:** `7b64053` (GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes were minor — test fixture correction and cosmetic line formatting. No scope creep. All functionality and acceptance criteria met as specified.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None — no external service configuration required. All dependencies are internal code modules from prior phases.

## Next Phase Readiness
- SCORE-03 (prioritized recommendations) and SCORE-04 (recommendations in report) are now complete
- ScoreReport is fully populated — Phase 6 (CLI) and Phase 7 (Streamlit) can consume recommendations directly
- All 20 scorer tests pass, providing a reliable foundation for downstream consumers

---
*Phase: 05-scorer-report*
*Completed: 2026-05-04*
