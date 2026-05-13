---
phase: 07-streamlit-dashboard
plan: 03
subsystem: testing
tags: [streamlit, pytest, apptest, functional-testing, dashboard]

# Dependency graph
requires:
  - phase: 07-streamlit-dashboard
    provides: "app.py dashboard with score hero, module expanders, recommendations, error display, and st.cache_data wrapper"
  - phase: 05-scorer-report
    provides: "ScoreReport dataclass and run_pipeline orchestrator"
provides:
  - "Functional test coverage for all 6 DASH requirements using streamlit.testing.v1.AppTest"
  - "13 test functions verifying URL input, pipeline trigger, spinner, score rendering, grade colors, module expanders, progress bars, recommendations, caching, and error display"
affects: [07-streamlit-dashboard, testing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Patching src.checker.orchestrator.run_pipeline for AppTest (not app-local names)"
    - "Using unique URLs in dashboard tests to avoid st.cache_data cross-test contamination"
    - "Accessing AppTest elements via .value (not str()) and subheader (not markdown for headings)"

key-files:
  created:
    - tests/test_dashboard.py
  modified: []

key-decisions:
  - "Patch src.checker.orchestrator.run_pipeline instead of app-local names (AppTest doesn't resolve local function names)"
  - "Use unique URLs per test to prevent st.cache_data cross-test cache hits in shared process memory"
  - "Check at.subheader for section headings (st.subheader renders Subheader elements, not Markdown)"
  - "Access AppTest element content via .value attribute (str() returns class repr, not text)"
  - "Verify expander children via .children dict (at.progress doesn't exist; progress bars are UnknownElement inside expanders)"
  - "Check session state via direct key access (SafeSessionState doesn't support .get())"

patterns-established:
  - "AppTest patching: always target source module via full dotted path (e.g. src.checker.orchestrator.run_pipeline)"
  - "Cache isolation: use unique URL perts to avoid cross-test cache contamination"
  - "Element inspection: use .value for Warning/Markdown/Error, .label for Metric/Expander, .children for nested expander content"

requirements-completed: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06]

# Metrics
duration: 22min
completed: 2026-05-13
---

# Phase 7 Plan 3: Dashboard Functional Tests Summary

**Functional test suite covering 6 DASH requirements with 13 AppTest-based test functions, all passing**

## Performance

- **Duration:** 22 min
- **Started:** 2026-05-13T15:29:37Z
- **Completed:** 2026-05-13T15:51:16Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments
- Created 13 functional tests using `streamlit.testing.v1.AppTest` covering all 6 DASH requirements
- DASH-01: URL input triggers pipeline, empty URL shows warning (2 tests)
- DASH-02: Loading spinner verified via app completion without exception (1 test)
- DASH-03: Score metric rendered with value, grade badge with correct hex color for all grades A-F (2 tests)
- DASH-04: Four module expanders with correct labels and nested content including progress bars (2 tests)
- DASH-05: Recommendations rendered with priority badges, empty recommendations not rendered (2 tests)
- DASH-06: Cache prevents re-execution on same URL, new URL triggers fresh pipeline call (2 tests)
- D-04: Verb error display and empty error state (2 tests)

## Task Commits

1. **Task 1: Create test_dashboard.py with AppTest functional tests** - `209f3d6` (test)

## Files Created/Modified
- `tests/test_dashboard.py` - 13 test functions covering URL input, pipeline trigger, spinner, score rendering, grade colors, module expanders, progress bars, recommendations, caching, and error display

## Decisions Made
- **Patch target:** Source module `src.checker.orchestrator.run_pipeline` rather than `app.run_pipeline` or `app.analyze_url`. AppTest.from_file doesn't resolve local function names for `unittest.mock.patch`.
- **Cache isolation:** Unique URLs per test (e.g., `https://example.com/cache-keep`, `https://example.com/A`) to prevent `st.cache_data` cross-test contamination. Cache storage is shared across AppTest instances in the same process.
- **Element access:** Use `.value` for Warning, Markdown, Error elements (not `str()` which returns class repr). Use `.label` for Metric and Expander. Section headings are `at.subheader` (Subheader elements), not Markdown.
- **Progress bars:** Expander children include progress bars as `UnknownElement()`. Verify via `len(at.expander[0].children) >= 1` rather than `at.progress` (which doesn't exist).
- **Session state:** `SafeSessionState` doesn't support `.get()`. Use direct key access with try/except KeyError for optional keys.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed patching target for AppTest module loading**
- **Found during:** Task 1 (initial test run)
- **Issue:** Plan specified `patch("app.run_pipeline")` and `patch("app.analyze_url")`, but AppTest.from_file doesn't resolve the module under the name `"app"`. Mock was never called.
- **Fix:** Changed all patches to `patch("src.checker.orchestrator.run_pipeline")` targeting the source module. Since `analyze_url` is a local function inside app.py and can't be patched via `mock.patch`, all tests use run_pipeline at the source level.
- **Files modified:** `tests/test_dashboard.py` (all 11 patching tests)
- **Verification:** All 13 tests pass, mock_run.call_count assertions verify correct behavior
- **Committed in:** `209f3d6`

**2. [Rule 1 - Bug] Fixed AppTest element API mismatches**
- **Found during:** Task 1 (incremental test runs)
- **Issue:** Multiple element access patterns in the plan didn't match AppTest's actual API:
  - `str(at.warning[0])` returns `"Warning()"`, not the message text. Fixed to `at.warning[0].value`.
  - `str(md)` for Markdown returns `"Markdown()"`, not the content. Fixed to `md.value` for all markdown assertions.
  - `str(at.error[0])` returns `"Error()"`. Fixed to `at.error[0].value`.
  - `at.progress` doesn't exist (progress bars are `UnknownElement` inside expanders). Fixed to check `len(at.expander[0].children)`.
  - Expander has no `set_value` method. Fixed cache test to use `text_input.set_value` as widget interaction.
  - `at.session_state.get()` doesn't exist (`SafeSessionState` has no `.get()`). Fixed to direct key access with try/except.
  - "Recommendations" heading is a `st.subheader`, not `st.markdown`. Fixed to check `at.subheader`.
- **Files modified:** `tests/test_dashboard.py` (8 tests affected)
- **Verification:** All assertions pass against actual AppTest element types
- **Committed in:** `209f3d6`

**3. [Rule 1 - Bug] Fixed cross-test cache contamination**
- **Found during:** Task 1 (test_grade_badge_color and test_recommendations_empty_not_rendered failures)
- **Issue:** `st.cache_data` storage is shared across `AppTest.from_file()` calls in the same process. Tests using the same URL (e.g., `"https://example.com"`) would receive cached results from earlier tests with different mock data.
- **Fix:** Used unique URLs in tests where specific mock data matters: grade tests (`/A`, `/B`, etc.), empty recommendations (`/empty-recs`), errors test (`/with-errors`), cache tests (`/cache-keep`, `/cache-new-1`, `/cache-new-2`).
- **Files modified:** `tests/test_dashboard.py` (4 tests)
- **Verification:** `test_grade_badge_color` passes for all 5 grades; `test_recommendations_empty_not_rendered` correctly sees no Recommendations subheader
- **Committed in:** `209f3d6`

---

**Total deviations:** 3 auto-fixed (all Rule 1 - Bugs)
**Impact on plan:** All fixes necessary for tests to pass correctly against the actual AppTest API and Streamlit cache behavior. No scope changes.

## Issues Encountered
- AppTest's module loading mechanism doesn't register files under their filename as a module name, making `patch("app.xxx")` ineffective. Resolved by patching the source module.
- Streamlit's `st.cache_data` uses process-global memory storage in testing, causing cache hits across separate `AppTest.from_file()` calls. Resolved with unique URLs.

## Next Phase Readiness
- All 6 DASH requirements have passing functional test coverage
- Full test suite (orchestrator 8 + dashboard 13 = 21 tests) passes green
- Ready for Phase 7 verification and sign-off

---
*Phase: 07-streamlit-dashboard*
*Completed: 2026-05-13*
