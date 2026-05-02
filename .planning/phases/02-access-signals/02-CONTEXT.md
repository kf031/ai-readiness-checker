# Phase 2: Access Signals — Context

**Gathered:** 2026-05-03
**Status:** Ready for planning
**Source:** Inline discussion

<domain>
## Phase Boundary

Analyze AI bot access permissions (robots.txt) and llms.txt presence for any website. Produces scored module outputs consumed by Phase 5 scorer.
</domain>

<decisions>
## Implementation Decisions

### robots.txt Scoring Formula
Start at 0.5 baseline. Each of the 7 AI bots: allowed = +0.07, blocked = -0.07, not_mentioned = 0.0.
This gives a range of 0.01 (all 7 blocked) to 0.99 (all 7 allowed).
Missing robots.txt = 0.5.

### robots.txt Fetch Failures
Distinguish between error types:
- 404 / file not found → treated as "missing" = 0.5
- Connection errors / timeouts / server errors → worse score than missing (e.g., 0.3) since these indicate infrastructure problems, not deliberate bot policy
- Must not crash the pipeline — return a partial result with error info

### llms.txt Validation
Check existence AND format validity per the llms.txt spec. Not just a binary found/not-found.
Malformed but present = different score than valid and present.

### Data Contracts
Typed dataclasses for module outputs following Phase 1 pattern:
- `RobotsResult` with per-bot breakdown (bot name, status, rule line)
- `LlmsResult` with found, valid, content_preview fields

### Concurrency
Fetch robots.txt and llms.txt concurrently (asyncio/httpx). Fall back to sequential if concurrent approach fails during testing.

</decisions>

<deferred>
## Deferred Ideas

None — all v1 requirements (BOT-01, BOT-02, LLMS-01, LLMS-02) covered.
</deferred>

---

*Phase: 02-access-signals*
*Context gathered: 2026-05-03 via inline discussion*
