---
phase: 4
slug: content-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_content.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_content.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CONT-01 | T-4-01 | Text capped at 1MB before NLP | unit | `pytest tests/test_content.py -v` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | CONT-02 | T-4-02 | Division-by-zero guard for empty pages | unit | `pytest tests/test_content.py -v` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | CONT-03 | T-4-03 | spaCy model missing → clear error, not crash | unit | `pytest tests/test_content.py -v` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | CONT-04 | T-4-04 | Heading counts bounded by BS4 parse tree | unit | `pytest tests/test_content.py -v` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 2 | CONT-05 | T-4-05 | Question regex bounded to avoid ReDoS | unit | `pytest tests/test_content.py -v` | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 2 | CONT-06 | T-4-06 | Score clamped to [0.0, 1.0] | unit | `pytest tests/test_content.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_content.py` — covers all 6 CONT-* requirements
- [ ] `tests/conftest.py` — add CONTENT_HTML_* fixtures (text-heavy, FAQ-style, thin, no-heading, multi-entity)
- [ ] `pip install textstat spacy && python -m spacy download en_core_web_sm`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live content analysis on real webpage | CONT-01..CONT-06 | Requires real public website with varied content | `fetch_url('https://en.wikipedia.org/wiki/Example')` — verify readability, entities, headings, QA density scores are plausible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
