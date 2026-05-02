---
phase: 2
slug: access-signals
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | pyproject.toml (already configured) |
| **Quick run command** | `pytest tests/test_robots.py tests/test_llms.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_robots.py tests/test_llms.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | BOT-01 | T-2-01 | N/A | unit | `pytest tests/test_robots.py -v` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | BOT-02 | T-2-02 | N/A | unit | `pytest tests/test_robots.py -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | LLMS-01 | T-2-03 | N/A | unit | `pytest tests/test_llms.py -v` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | LLMS-02 | T-2-04 | N/A | unit | `pytest tests/test_llms.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_robots.py` — stubs for BOT-01, BOT-02
- [ ] `tests/test_llms.py` — stubs for LLMS-01, LLMS-02
- [ ] `tests/conftest.py` — robots.txt and llms.txt fixtures (extend existing)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live robots.txt fetch | BOT-01 | Requires real public website | `fetch_url('https://example.com/robots.txt')` — verify parsed result |
| Live llms.txt fetch | LLMS-01 | Requires real public website | `fetch_url('https://example.com/llms.txt')` — verify result struct |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
