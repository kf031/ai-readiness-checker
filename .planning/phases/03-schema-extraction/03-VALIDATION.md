---
phase: 3
slug: schema-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_schema.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_schema.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SCHEMA-01 | T-3-01 | extruct handles untrusted HTML via errors="log" | unit | `pytest tests/test_schema.py -v` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SCHEMA-02 | T-3-02 | Type normalization prevents injection via @type field | unit | `pytest tests/test_schema.py -v` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | SCHEMA-03 | T-3-03 | Score bounded 0.0-1.0 regardless of input | unit | `pytest tests/test_schema.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schema.py` — stubs for SCHEMA-01, SCHEMA-02, SCHEMA-03
- [ ] `tests/conftest.py` — 6-8 HTML fixtures: JSON-LD Product, microdata FAQPage, @graph multi-type, RDFa Product, malformed JSON-LD, empty page, OpenGraph product, full multi-format page

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live schema extraction from real website | SCHEMA-01 | Requires real public website with structured data | `fetch_url('https://example.com')` — verify extruct returns structured data without crashing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
