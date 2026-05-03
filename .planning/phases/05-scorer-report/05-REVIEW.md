---
phase: 05-scorer-report
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/checker/__init__.py
  - src/checker/contracts.py
  - src/checker/scorer.py
  - tests/test_scorer.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the Phase 5 scorer and report generator (`scorer.py`), its data contracts (`contracts.py` `ScoreReport`), re-exports (`__init__.py`), and tests (`test_scorer.py`). The implementation is generally sound — the weighted scoring math is correct, grade boundary logic matches the spec, recommendation generation is well-structured, and test coverage is good (13 tests covering boundary conditions and edge cases).

Three warnings were found: two stale docstrings that misrepresent the current recommendation behavior, and one public function (`compute_overall_score`) that lacks input validation and will crash with a `KeyError` if called with an incomplete score dict. Two info-level items cover a minor type annotation gap and a test reliability concern.

No critical issues were found — no security vulnerabilities, data loss risks, or crash paths in the primary `generate_report` call chain.

---

## Warnings

### WR-01: `generate_report` docstring claims recommendations are not implemented

**File:** `src/checker/scorer.py:326-328`
**Issue:** The docstring for `generate_report` states the function returns a report with "empty recommendations (filled in Plan 02)". This is stale — the implementation at line 350-352 actually calls `generate_recommendations()` which produces real, non-empty recommendations for each module. Any developer reading this docstring would be misled about the function's current behavior.
**Fix:** Update the docstring to accurately describe the recommendations field:
```python
Returns:
    ScoreReport with overall_score, grade, module_breakdown,
    prioritized recommendations from all four modules, and UTC timestamp.
```

Also update the corresponding `ScoreReport.recommendations` field docstring in `contracts.py` (line 192-194), which says "Empty list when recommendations are not yet implemented (Plan 02)."

---

### WR-02: `compute_overall_score` crashes with KeyError on incomplete input dict

**File:** `src/checker/scorer.py:80-93`
**Issue:** `compute_overall_score` iterates over `MODULE_WEIGHTS` keys and directly indexes into the `scores` dict. If any required key (`"robots"`, `"llms_txt"`, `"schema"`, `"content"`) is missing from the input dict, the function raises an unhandled `KeyError`. While the internal call chain always passes a complete dict (via `_extract_scores`), `compute_overall_score` is a public module-level function (no leading underscore) and is directly tested in `test_scorer.py`. External callers could reasonably call it with incomplete data.
**Fix:** Add key validation or use `.get()` with defaults:
```python
def compute_overall_score(scores: dict[str, float]) -> float:
    weighted = sum(
        scores.get(key, 0.0) * MODULE_WEIGHTS[key]
        for key in MODULE_WEIGHTS
    )
    return round(weighted * 100.0, 1)
```
Or alternatively, validate keys upfront and raise a clear `ValueError` with the missing key name.

---

### WR-03: `letter_grade` has no input validation for out-of-range scores

**File:** `src/checker/scorer.py:96-108`
**Issue:** Unlike `_validate_score` (which clamps module scores to [0.0, 1.0] with a warning), `letter_grade` performs no validation on its `overall_score` input. A caller passing a value outside [0.0, 100.0] receives a semantically questionable result — e.g., `letter_grade(-10.0)` returns `"F"` silently, and `letter_grade(150.0)` returns `"A"` silently. While `generate_report` always passes a valid score from `compute_overall_score`, this function is public and directly tested.
**Fix:** Add a warning for out-of-range values, consistent with the pattern used in `_validate_score`:
```python
def letter_grade(overall_score: float) -> str:
    if not math.isfinite(overall_score):
        logger.warning(f"Non-finite overall_score ({overall_score}); returning 'F'")
        return "F"
    if overall_score < 0.0 or overall_score > 100.0:
        logger.warning(
            f"overall_score {overall_score} outside [0.0, 100.0]; clamping"
        )
    clamped = max(0.0, min(100.0, overall_score))
    for threshold, grade in GRADE_BOUNDARIES:
        if clamped >= threshold:
            return grade
    return "F"
```

---

## Info

### IN-01: `SchemaAnalysis.type_details` uses untyped inner dict

**File:** `src/checker/contracts.py:132`
**Issue:** The `type_details` field is annotated as `dict[str, dict]` — the inner dict's value types are unspecified. The docstring describes the intended structure (`"count": int`, `"formats": list[str]`), but the type annotation doesn't enforce or document this. Mypy/pyright will treat the inner values as `Any`.
**Fix:** Use `TypedDict` or at minimum `dict[str, dict[str, object]]` to make the nested structure explicit. If downstream code relies on specific keys, a `TypedDict` would catch key typos at static analysis time.

---

### IN-02: Test `test_json_serializable` uses `default=str` which masks non-serializable objects

**File:** `tests/test_scorer.py:151`
**Issue:** `json.dumps(report_dict, default=str)` converts any non-JSON-serializable object to its string representation rather than raising `TypeError`. This means the test can pass even if the report dict contains objects that are not truly JSON-serializable (e.g., `datetime` would become a string like `"2026-05-04 00:00:00+00:00"` instead of failing). The test's purpose is to verify the report is suitable for JSON output, so silent coercion defeats that purpose.
**Fix:** Either:
1. Remove `default=str` and verify no `TypeError` is raised (fail if it is), or:
2. Round-trip through `json.dumps`/`json.loads` and verify key fields survive intact (e.g., `assert parsed["overall_score"] == report.overall_score`).

Note: this is an info-level item because the timestamp IS the only non-JSON-native type, and `asdict` does handle datetimes on newer Python versions. The `default=str` just makes the test less sensitive to future regressions.

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
