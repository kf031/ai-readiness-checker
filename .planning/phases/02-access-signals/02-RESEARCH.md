# Phase 2: Access Signals — Research

**Researched:** 2026-05-03
**Domain:** robots.txt parsing + llms.txt format validation
**Confidence:** HIGH

## Summary

Phase 2 adds two new analysis modules to the AI Readiness Checker: a robots.txt analyzer that reports access status for 7 AI bot user-agent tokens, and an llms.txt validator that checks file presence and format conformance. Both modules fetch resources from the target site's root path (`/robots.txt`, `/llms.txt`) concurrently using httpx.AsyncClient, then produce typed dataclass results consumed by the Phase 5 scorer.

The primary technical finding is that Python's stdlib `urllib.robotparser` CAN be used for parsing robots.txt into structured groups, but its built-in `can_fetch()` method has two defects that make it unsuitable for this project's analysis use case: (1) it uses first-match-wins instead of RFC 9309 longest-match-wins for path rules, and (2) its user-agent matching uses overly broad substring matching (`User-agent: bot` would match `GPTBot`). The recommended approach is to use `urllib.robotparser` for the parsing phase only (extracting entries with their useragents and rulelines), then implement our own precise case-insensitive exact-token matching for the 7 AI bots.

**Primary recommendation:** Use urllib.robotparser for parsing robots.txt into structured groups, implement custom exact-token user-agent matching for the 7 bots, and use httpx.AsyncClient with asyncio.gather for concurrent fetching of robots.txt and llms.txt.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fetch robots.txt from target site | API/Backend | — | HTTP GET to remote server; runs in the checker tool's analysis pipeline |
| Fetch llms.txt from target site | API/Backend | — | Same as above; runs concurrently with robots.txt fetch |
| Parse robots.txt into User-agent groups | API/Backend | — | Pure string parsing; no browser involvement |
| Match AI bot tokens against parsed groups | API/Backend | — | String comparison logic; runs in checker |
| Validate llms.txt markdown structure | API/Backend | — | Text analysis; content may have been authored by humans but validation is algorithmic |
| Compute per-bot access status (allowed/blocked/not_mentioned) | API/Backend | — | Business logic derived from parsed robots.txt rules |
| Produce RobotsResult and LlmsResult dataclasses | API/Backend | — | Data contracts consumed by Phase 5 scorer |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
1. **robots.txt scoring formula**: Baseline 0.5. Each of 7 AI bots: allowed = +0.07, blocked = -0.07, not_mentioned = 0.0. Range: 0.01 (all blocked) to 0.99 (all allowed). Missing robots.txt = 0.5.
2. **Fetch error differentiation**: 404 = missing (score 0.5). Connection errors/timeouts/server errors = worse score (0.3). Never crash.
3. **llms.txt validation**: Check format validity per spec, not just existence. Malformed but present gets a different score than valid and present.
4. **Data contracts**: Typed dataclasses (RobotsResult, LlmsResult) following Phase 1 FetchResult pattern.
5. **Concurrency**: Try concurrent fetch with asyncio/httpx first. Fall back to sequential if it fails.

### Claude's Discretion
- Exact field design for RobotsResult and LlmsResult dataclasses
- robots.txt parsing library choice (stdlib vs third-party)
- llms.txt validation criteria (which format rules to enforce)
- Error taxonomy for fetch failures
- Module file organization

### Deferred Ideas (OUT OF SCOPE)
None — all v1 requirements (BOT-01, BOT-02, LLMS-01, LLMS-02) covered.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOT-01 | Parse robots.txt and report access status (allowed / blocked / not_mentioned) for all 7 AI bots: GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot-Extended, Amazonbot | urllib.robotparser for parsing + custom exact-token matching (not can_fetch) |
| BOT-02 | Bot access results produce 0.0–1.0 score using formula: baseline 0.5, each allowed +0.07, each blocked -0.07, not_mentioned +0.00, missing = 0.5 | Scoring logic in robots_txt module with RobotsResult containing per-bot breakdown |
| LLMS-01 | Check for /llms.txt at site root; report found/not-found; 500-char content preview if present | httpx fetch to root path; llms.txt spec from llmstxt.org defines format |
| LLMS-02 | llms.txt result produces binary score: found = 1.0, not found = 0.0 | LlmsResult.found field consumed directly by Phase 5 scorer |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| urllib.robotparser | stdlib (Python 3.13) | Parse robots.txt into User-agent groups and rule lines | Zero-dependency; handles line parsing, comments, blank lines, multi-group extraction. We override matching logic but reuse the parser. |
| httpx | 0.28.1 | Async HTTP client for concurrent robots.txt + llms.txt fetch | Already installed; supports asyncio; shares requests-like API; single AsyncClient for connection pooling |
| markdown-it-py | 4.0.0 | Markdown parsing for llms.txt validation | Already installed (transitive dep of Rich); provides token-level access to markdown elements for H1/H2/link checks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Coroutine scheduling for concurrent fetches | Required by locked concurrency decision |
| re | stdlib | robots.txt path matching with `*` and `$` wildcards | When evaluating Allow/Disallow rules (RFC 9309 pattern matching) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| urllib.robotparser (parsing only) | Manual regex parsing | Manual handles non-standard syntax robustly but duplicates comment-stripping and line-continuation logic that urllib already has |
| urllib.robotparser (parsing only) | robotspy 0.13.0 | robotspy is a third-party parser supporting RFC 9309 but installed version has import issues; adds dependency for no clear gain over stdlib |
| markdown-it-py for validation | Manual regex (H1 check + link detection) | Manual is simpler but fragile — misses edge cases like code-fenced `#` or escaped brackets in links; markdown-it-py provides token-level AST |
| httpx.AsyncClient | ThreadPoolExecutor + requests | TPE is simpler (no async/await) and integrates cleanly with existing sync codebase, but the user locked asyncio/httpx; TPE serves as natural sequential fallback |

**Installation:**
```bash
# httpx already installed (0.28.1) — add to pyproject.toml dependencies
# markdown-it-py already installed (4.0.0) — no action needed (Rich dependency)
# No new pip installs required
```

**Version verification:**
- httpx: 0.28.1 [VERIFIED: pip show httpx] — current as of 2026-05-03
- markdown-it-py: 4.0.0 [VERIFIED: import + version check] — stable
- urllib.robotparser: bundled with CPython 3.13.9 [VERIFIED: import check]
- robotspy: 0.13.0 installed but fails to import (package/module name mismatch) — NOT RECOMMENDED

### Update pyproject.toml
Add `"httpx>=0.28,<1.0"` to the dependencies list in pyproject.toml. This is required because httpx is currently installed as a transitive dependency but not declared as a direct dependency of the project.

## Architecture Patterns

### System Architecture Diagram

```
                         Target Website
                              |
                    ┌─────────┴──────────┐
                    |                    |
              GET /robots.txt      GET /llms.txt
                    |                    |
              ┌─────┴─────┐       ┌─────┴─────┐
              | httpx.Async |     | httpx.Async |
              | Client.get  |     | Client.get  |
              └─────┬─────┘       └─────┬─────┘
                    |                    |
              asyncio.gather() ──────────┘
                    |
          ┌─────────┴─────────┐
          |                   |
    robots_txt module    llms_txt module
          |                   |
  ┌───────┴───────┐    ┌──────┴──────┐
  | urllib.robot  |    | markdown-it  |
  | parser.parse  |    | -py tokens   |
  └───────┬───────┘    └──────┬──────┘
          |                   |
  Custom exact-token     H1 presence check
  UA matching for        H2 structure check
  7-bot product tokens   Link format check
          |                   |
  ┌───────┴───────┐    ┌──────┴──────┐
  | RobotsResult  |    | LlmsResult  |
  └───────────────┘    └─────────────┘
          |                   |
          └─────────┬─────────┘
                    |
              Phase 5 Scorer
```

### Recommended Project Structure
```
src/checker/
├── __init__.py
├── contracts.py         # +RobotsResult, +LlmsResult, +BotStatus
├── crawler.py           # existing — unchanged
├── robots_txt.py        # NEW: robots.txt fetch + analysis module
├── llms_txt.py          # NEW: llms.txt fetch + validation module
└── access_fetcher.py    # NEW: concurrent fetch orchestrator
```

### Pattern 1: Async Concurrent Fetch with Sequential Fallback
**What:** Use httpx.AsyncClient with asyncio.gather for two parallel GETs. Wrap in try/except for any asyncio-related errors, falling back to sequential httpx client calls.
**When to use:** This is the locked concurrency approach. The fallback exists for environments where the event loop is unavailable or conflicts with other async code.
**Example:**
```python
# Source: httpx official docs + standard asyncio pattern
import asyncio
import httpx

async def fetch_both(base_url: str) -> tuple:
    """Fetch robots.txt and llms.txt concurrently. Returns raw responses."""
    robots_url = base_url.rstrip('/') + '/robots.txt'
    llms_url = base_url.rstrip('/') + '/llms.txt'

    async with httpx.AsyncClient(timeout=10.0) as client:
        robots_task = client.get(robots_url)
        llms_task = client.get(llms_url)
        robots_resp, llms_resp = await asyncio.gather(
            robots_task, llms_task, return_exceptions=True
        )
    return robots_resp, llms_resp


def fetch_access_signals(base_url: str):
    """Synchronous wrapper with fallback."""
    try:
        return asyncio.run(fetch_both(base_url))
    except Exception:
        # Fallback: sequential
        with httpx.Client(timeout=10.0) as client:
            robots = client.get(robots_url(base_url))
            llms = client.get(llms_url(base_url))
        return robots, llms
```

### Pattern 2: urllib.robotparser for Parsing, Custom Matching for Analysis
**What:** Use `RobotFileParser.parse()` to populate `.entries` and `.default_entry`, then manually walk those entries to find the first group whose useragent list contains our bot's exact token (case-insensitive). Evaluate the Allow/Disallow rules for the root path `/` to determine allowed vs blocked.
**When to use:** Every time we analyze a robots.txt. Never use `.can_fetch()` — it has known RFC 9309 violations and substring matching issues.
**Example:**
```python
# Source: urllib.robotparser source code inspection [VERIFIED]
from urllib.robotparser import RobotFileParser

BOT_TOKENS = [
    "GPTBot", "ClaudeBot", "PerplexityBot", "CCBot",
    "Google-Extended", "Applebot-Extended", "Amazonbot",
]

def analyze_robots(robots_text: str) -> dict[str, str]:
    """Return per-bot status: 'allowed', 'blocked', or 'not_mentioned'."""
    rp = RobotFileParser()
    rp.parse(robots_text.splitlines())

    results = {}
    for token in BOT_TOKENS:
        token_lower = token.lower()
        # Check specific groups first
        found = False
        for entry in rp.entries:
            if any(token_lower == ua.lower() for ua in entry.useragents):
                found = True
                # Check Allow/Disallow for root path
                results[token] = _eval_rules_for_root(entry)
                break
        if not found and rp.default_entry:
            # Bot not specifically mentioned, but * catch-all exists
            results[token] = _eval_rules_for_root(rp.default_entry)
        elif not found:
            results[token] = "not_mentioned"
    return results

def _eval_rules_for_root(entry) -> str:
    """Check if the entry's rules allow or block the root path '/'."""
    for rule in entry.rulelines:
        if rule.applies_to("/"):
            return "allowed" if rule.allowance else "blocked"
    return "allowed"  # No matching rule = allowed
```

### Pattern 3: llms.txt Format Validation via markdown-it-py Tokens
**What:** Use markdown-it-py's tokenizer to check: (a) first non-empty line is an H1 heading, (b) H2 sections exist and contain list items with markdown links, (c) no heading elements appear between H1 and H2 sections.
**When to use:** Whenever llms.txt returns 200 OK. A 404 means not found (no validation needed).
**Example:**
```python
# Source: markdown-it-py API docs + llmstxt.org spec [CITED]
from markdown_it import MarkdownIt

def validate_llms_txt(text: str) -> tuple[bool, list[str]]:
    """Return (is_valid, list_of_errors)."""
    errors = []
    md = MarkdownIt()
    tokens = md.parse(text)

    # Extract heading and link structure
    headings = [t for t in tokens if t.type == 'heading_open']
    links = [t for t in tokens if t.type == 'link_open']

    # Rule 1: First heading must be H1
    if not headings:
        errors.append("Missing H1 heading (required by spec)")
    elif headings[0].tag != 'h1':
        errors.append(f"First heading is <{headings[0].tag}>, expected <h1>")

    # Rule 2: Must have at least one H2 section
    h2_headings = [h for h in headings if h.tag == 'h2']
    if not h2_headings:
        errors.append("No H2 file-list sections found")

    # Rule 3: H2 sections must contain markdown links
    # (Simplified check — a full check tracks token nesting)
    if h2_headings and not links:
        errors.append("H2 sections present but no markdown links found")

    return len(errors) == 0, errors
```

### Anti-Patterns to Avoid
- **Using `urllib.robotparser.can_fetch()` for analysis**: The `applies_to()` method uses `"agent in useragent"` substring matching — `User-agent: bot` would incorrectly match `GPTBot`. Also uses first-match-wins for path rules, violating RFC 9309. Use custom exact-token matching on parsed entries instead.
- **Hardcoding full User-Agent strings**: The `can_fetch()` useragent parameter should be the product token (e.g., `"GPTBot"`), not the full HTTP header string. But for our analysis, we pass the exact product token and match against entry.useragents with case-insensitive equality. [VERIFIED: source code inspection of `Entry.applies_to()`]
- **Instantiating AsyncClient inside a loop**: httpx docs warn: "make sure you're not instantiating multiple client instances — for example by using `async with` inside a 'hot loop'." One `AsyncClient` instance handles both requests. [CITED: python-httpx.org/async/]
- **Blocking the event loop**: Don't mix `requests.get()` (sync) with `asyncio.run()`. If the fallback is needed, use synchronous `httpx.Client`, not `requests`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| robots.txt line parsing | Manual regex for User-agent/Allow/Disallow/Sitemap extraction + comment stripping + blank line handling + multi-line continuation | `urllib.robotparser.RobotFileParser.parse()` | 50+ lines of edge-case handling (comments, blank lines, multi-group separation, line continuations, case normalization) already solved in stdlib |
| HTTP client for robots.txt/llms.txt fetch | Custom socket/asyncio code | `httpx` (already installed, matches locked concurrency decision) | HTTP redirects, TLS, timeouts, connection pooling, header parsing all handled |
| Markdown AST parsing | Manual regex for heading detection (fails on code-fenced `#`, escaped brackets) | `markdown-it-py` (already installed as Rich dependency) | Token-level parsing catches edge cases that regex-based heading/link detection misses |
| Thread pool for concurrent fetches | `concurrent.futures.ThreadPoolExecutor` hand-management | `httpx.AsyncClient` + `asyncio.gather` (locked decision) | Already locked by user; TPE serves as fallback only |

**Key insight:** This phase can be built with zero new pip installs — all three core libraries (urllib.robotparser, httpx, markdown-it-py) are already present in the environment. Only pyproject.toml needs updating to declare httpx as a direct dependency.

## Common Pitfalls

### Pitfall 1: urllib.robotparser Substring Matching False Positives
**What goes wrong:** `Entry.applies_to()` checks `if agent in useragent`, meaning `User-agent: bot` matches `GPTBot` because `"bot"` is a substring of `"gptbot"`. This would report GPTBot as "mentioned" (and potentially blocked) when the site only intended to target a generic `bot` crawler.
**Why it happens:** The stdlib follows a loose interpretation of RFC 9309 substring matching but does it backwards — it checks if the robots.txt token is a substring of the query useragent, not the other way around. For analysis, this means tokens like `"bot"` or `"crawler"` match everything.
**How to avoid:** Do not use `can_fetch()` or `entry.applies_to()`. After populating entries via `rp.parse()`, manually walk `entry.useragents` and check case-insensitive EXACT equality against each bot's canonical product token.
**Warning signs:** A test site with `User-agent: bot` returns all 7 AI bots as "mentioned" when only generic bots were intended.

### Pitfall 2: First-Match-Wins Path Evaluation
**What goes wrong:** If robots.txt says `Allow: /admin/public/` then `Disallow: /admin/`, urllib.robotparser returns whichever appears first. Per RFC 9309, the longest matching rule should win regardless of order.
**Why it happens:** `RobotFileParser.can_fetch()` iterates entries in source order and returns on first match. It does not implement the longest-match algorithm required by RFC 9309 section 2.2.2.
**How to avoid:** We only evaluate the root path `/` to determine overall bot access (allowed vs blocked), so longest-match is rarely relevant. But if we ever need path-specific checking, implement longest-match evaluation by comparing rule path lengths after collecting all matching rules.
**Warning signs:** Known from the dev.to article "Python's urllib.robotparser Is Subtly Wrong" [CITED].

### Pitfall 3: Google-Extended Has No HTTP User-Agent
**What goes wrong:** Google-Extended is purely a robots.txt control token — Google's crawlers use the `Googlebot` user-agent string in HTTP requests. If someone tries to verify Google-Extended by making an HTTP request with that User-Agent, it won't work as expected.
**Why it happens:** As Google's documentation states, Google-Extended crawling "is done with existing Google user agent strings; the robots.txt user-agent token is used in a control capacity." [CITED: developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers]
**How to avoid:** We only analyze the robots.txt file content — we never make HTTP requests using bot User-Agents. The Google-Extended token is used exclusively for matching against `User-agent:` lines in robots.txt. This is correct for our analysis use case.
**Warning signs:** Not applicable — we're not doing HTTP verification of bot access. But note for documentation: explain that Google-Extended status reflects robots.txt policy only.

### Pitfall 4: robots.txt at Subdomain vs Root Domain
**What goes wrong:** A site at `https://blog.example.com` may have different robots.txt rules than `https://example.com`. Our tool only checks the URL's domain-level robots.txt.
**Why it happens:** robots.txt is per-origin (scheme + host + port). Subdomains are different origins.
**How to avoid:** We fetch robots.txt from the exact origin of the input URL. This is correct behavior — we analyze the URL the user gave us. Document that subdomain-specific analysis requires separate runs.
**Warning signs:** User inputs `https://docs.example.com/page` and wonders why results differ from `https://example.com/page`.

### Pitfall 5: llms.txt URI Encoding in Links
**What goes wrong:** llms.txt file list items may contain percent-encoded URLs or non-ASCII characters in link targets that break naive URL extraction.
**Why it happens:** The llms.txt spec uses standard markdown, which permits various link target formats including relative URLs, absolute URLs, and fragment-only links.
**How to avoid:** Extract link targets from markdown-it-py tokens (which handle encoding) rather than regex-matching `](url)`. For validation, we only check that links EXIST, not that they resolve.
**Warning signs:** llms.txt with `[page](/%E2%9C%93-check)` fails regex-based URL extraction but passes markdown-it-py token parsing.

## Code Examples

Verified patterns from official sources:

### Fetch robots.txt and llms.txt Concurrently
```python
# Source: httpx official docs async section + asyncio standard library [CITED: python-httpx.org/async/]
import asyncio
import httpx
from typing import Optional
from urllib.parse import urljoin

async def fetch_access_resources(base_url: str, timeout: float = 10.0):
    """Concurrently fetch robots.txt and llms.txt from the target site."""
    robots_url = urljoin(base_url, '/robots.txt')
    llms_url = urljoin(base_url, '/llms.txt')

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/plain,text/html,*/*',
        },
        follow_redirects=True,
    ) as client:
        robots_resp, llms_resp = await asyncio.gather(
            client.get(robots_url),
            client.get(llms_url),
            return_exceptions=True,
        )
    return robots_resp, llms_resp
```

### Custom Exact User-Agent Token Matching
```python
# Source: urllib.robotparser source code inspection [VERIFIED: 2026-05-03]
# Pattern derived from Entry.applies_to() but with EXACT matching instead of substring

BOT_TOKENS = [
    "GPTBot", "ClaudeBot", "PerplexityBot", "CCBot",
    "Google-Extended", "Applebot-Extended", "Amazonbot",
]

def find_bot_group(entries, default_entry, bot_token: str):
    """Find the first entry whose useragents contain bot_token (exact, case-insensitive).
    Falls back to default_entry (*) if no specific match.
    Returns (entry, is_explicit_match) or (None, False) for not_mentioned.
    """
    token_lower = bot_token.lower()
    for entry in entries:
        if any(token_lower == ua.lower() for ua in entry.useragents):
            return entry, True
    if default_entry:
        return default_entry, False
    return None, False
```

### Path Rule Evaluation with RFC 9309 Wildcards
```python
# Source: RFC 9309 section 2.2.2 [CITED: rfc-editor.org/rfc/rfc9309.html]
import re

def rule_matches_path(rule_path: str, request_path: str) -> bool:
    """Check if a robots.txt rule path matches a request path per RFC 9309.
    Handles * (any sequence) and $ (end anchor) wildcards.
    """
    # Escape regex metacharacters except * and $
    escaped = re.escape(rule_path)
    # * becomes .* (match any sequence)
    pattern = escaped.replace(r'\*', '.*')
    # $ stays as end anchor ($ is already a regex anchor)
    # But only if it appears literally at the end of the escaped pattern
    if pattern.endswith(r'\$'):
        pattern = pattern[:-2] + '$'
    return bool(re.match(pattern, request_path))
```

### llms.txt H1 Detection via markdown-it-py
```python
# Source: markdown-it-py API [VERIFIED: import check, version 4.0.0]
from markdown_it import MarkdownIt

def extract_llms_heading(text: str) -> Optional[str]:
    """Extract the H1 heading text from an llms.txt file.
    Returns None if no H1 found."""
    md = MarkdownIt()
    tokens = md.parse(text)

    for i, token in enumerate(tokens):
        if token.type == 'heading_open' and token.tag == 'h1':
            # The next inline token contains the heading text
            if i + 1 < len(tokens) and tokens[i + 1].type == 'inline':
                return tokens[i + 1].content
    return None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| robots.txt as informal convention with varying implementations | RFC 9309 formal standard (Sep 2022) | Google, Bing adopted RFC 9309 by 2023; Python stdlib still on pre-RFC behavior | urllib.robotparser uses deprecated first-match-wins; must override for correctness |
| Manual robots.txt blocklist per crawler | AI-specific opt-out tokens (Google-Extended, Applebot-Extended) | 2023-2024 as LLM training became contentious | We now have 7 distinct tokens to check, not just generic `*` |
| llms.txt non-existent | llms.txt as community standard (Jeremy Howard / AnswerDotAI, late 2024) | Adopted by major documentation sites and LLM tooling in 2025 | New file to fetch and validate; no legacy formats to worry about |
| Sequential HTTP fetches | Concurrent async fetches (httpx, aiohttp) | Standard practice since Python 3.7+ asyncio maturity | 2x faster for this phase's two-fetch pattern |

**Deprecated/outdated:**
- `reppy` (last release 2020, Python 3.8 max, unmaintained) — DO NOT USE
- `robotspy` (installed but import fails — package name mismatch) — DO NOT USE
- `urllib.robotparser.can_fetch()` for analysis purposes — uses pre-RFC 9309 matching — DO NOT USE for our bot classification; parse only, match manually

## Error Taxonomy

### robots.txt Fetch Error Classification

| HTTP Status / Error | Classification | Score | RobotFileParser Behavior |
|---------------------|---------------|-------|--------------------------|
| 200 OK | Success — parse and analyze | Per-bot formula | Normal parsing |
| 404 Not Found | Missing robots.txt | 0.5 | `read()` method sets `allow_all = True` on 404 |
| 401 Unauthorized | Missing (server blocks access) | 0.5 | `read()` sets `disallow_all = True` on 401 |
| 403 Forbidden | Missing (server blocks access) | 0.5 | `read()` sets `disallow_all = True` on 403 |
| 4xx (other) | Infrastructure error | 0.3 | `read()` sets `allow_all = True` |
| 5xx (any) | Infrastructure error | 0.3 | Exception raised by `read()` |
| Connection error | Infrastructure error | 0.3 | Exception raised by `read()` |
| Timeout | Infrastructure error | 0.3 | Exception raised by `read()` |
| Too many redirects | Infrastructure error | 0.3 | Exception raised |
| SSRF blocked | Pipeline blocked (should never happen for robots.txt URL) | 0.3 | N/A |

**Note:** We should NOT use `RobotFileParser.read()` for fetching. It uses `urllib.request.urlopen()` internally which does not use our Chrome 131 User-Agent and does not share our timeout settings. Instead, fetch with httpx (which gives us our own error classification), then pass the response text to `RobotFileParser.parse()`.

### llms.txt Fetch Error Classification

| HTTP Status / Error | Classification | Score | Validation |
|---------------------|---------------|-------|------------|
| 200 OK | Success — validate format | Valid=1.0, Invalid=varies | Full format validation |
| 404 Not Found | Not found | 0.0 | Skip validation |
| Connection error | Infrastructure error | 0.0 (with error info) | Skip validation |
| Timeout | Infrastructure error | 0.0 (with error info) | Skip validation |
| 5xx | Infrastructure error | 0.0 (with error info) | Skip validation |

### Error Propagation Rule
Both modules MUST return their result dataclass even on fetch failure. Set `fetch_error` field to the error type, set `bots` to all-not_mentioned (robots) or `found=False` (llms.txt), and populate `error_type` for Phase 5 scorer consumption. NEVER raise an exception from these modules.

## Data Contract Design

### RobotsResult
```python
@dataclass
class BotStatus:
    """Per-bot access status extracted from robots.txt."""
    bot_name: str          # e.g., "GPTBot"
    status: str            # "allowed" | "blocked" | "not_mentioned"
    rule_line: Optional[str]  # The Allow/Disallow line that determined status
    explicitly_mentioned: bool  # True if bot token appeared in a User-agent line

@dataclass
class RobotsResult:
    """Complete robots.txt analysis result.
    Consumed by Phase 5 scorer for the robots component (20% weight).
    """
    url: str                          # The URL whose robots.txt was analyzed
    exists: bool                      # robots.txt was fetched successfully (200 OK)
    status_code: Optional[int]        # HTTP status from fetch
    fetch_error: Optional[str]        # Error type if fetch failed (None if success)
    bots: list[BotStatus]             # Per-bot breakdown (always 7 items)
    raw_text: Optional[str]           # Raw robots.txt content (None if fetch failed)
    fetched_at: datetime              # UTC timestamp of fetch
```

### LlmsResult
```python
@dataclass
class LlmsResult:
    """Complete llms.txt analysis result.
    Consumed by Phase 5 scorer for the llms.txt component (15% weight).
    """
    url: str                          # The URL whose llms.txt was analyzed
    found: bool                       # llms.txt returned 200 OK
    status_code: Optional[int]        # HTTP status from fetch
    fetch_error: Optional[str]        # Error type if fetch failed (None if success)
    valid: Optional[bool]             # Format validity per spec (None if not found)
    validation_errors: list[str]      # Format violations (empty if valid or not found)
    content_preview: Optional[str]    # First 500 chars if found (None if not)
    raw_text: Optional[str]           # Full llms.txt content (None if not found)
    fetched_at: datetime              # UTC timestamp of fetch
```

**Design rationale:**
- `BotStatus.status` uses string literals ("allowed"/"blocked"/"not_mentioned") rather than enums to match the locked scoring formula terminology exactly. Phase 5 scorer maps these directly to +/-/0 adjustments.
- `RobotsResult.exists` is a convenience boolean for the Phase 5 scorer: if False, skip per-bot analysis and use score 0.5 or 0.3 depending on `fetch_error`.
- `LlmsResult.valid` is `Optional[bool]` because it's `None` when the file wasn't found — there's nothing to validate. The Phase 5 scorer checks `found` first, then `valid`.
- Both dataclasses include `raw_text` for debugging and report generation but these are not consumed by scoring logic.
- Integration with Phase 5 REQ BOT-03 (v2): `BotStatus` already carries per-bot breakdown, making CLI/UI display straightforward later.

## Runtime State Inventory

> Phase 2 is a greenfield addition (new modules), not a rename/refactor/migration. Skip this section.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_robots.py tests/test_llms.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOT-01 | All 7 bots classified correctly from parsed robots.txt | unit | `pytest tests/test_robots.py::test_all_bots_explicitly_mentioned -x` | No (Wave 0) |
| BOT-01 | Bot not in any User-agent line returns not_mentioned | unit | `pytest tests/test_robots.py::test_bot_not_mentioned -x` | No (Wave 0) |
| BOT-01 | `*` catch-all applies when no specific bot group exists | unit | `pytest tests/test_robots.py::test_catchall_applies -x` | No (Wave 0) |
| BOT-01 | Google-Extended token matched case-insensitively | unit | `pytest tests/test_robots.py::test_google_extended_caseless -x` | No (Wave 0) |
| BOT-02 | All 7 allowed = score 0.99 | unit | `pytest tests/test_robots.py::test_score_all_allowed -x` | No (Wave 0) |
| BOT-02 | All 7 blocked = score 0.01 | unit | `pytest tests/test_robots.py::test_score_all_blocked -x` | No (Wave 0) |
| BOT-02 | Score calculation from BotStatus list | unit | `pytest tests/test_robots.py::test_scoring_formula -x` | No (Wave 0) |
| BOT-02 | 404 returns score 0.5 | integration | `pytest tests/test_robots.py::test_missing_robots_txt -x` | No (Wave 0) |
| BOT-02 | Connection error returns score 0.3 | unit | `pytest tests/test_robots.py::test_robots_connection_error -x` | No (Wave 0) |
| LLMS-01 | Valid llms.txt detected as found + valid | unit | `pytest tests/test_llms.py::test_valid_llms_txt -x` | No (Wave 0) |
| LLMS-01 | 500-char content preview extracted | unit | `pytest tests/test_llms.py::test_content_preview -x` | No (Wave 0) |
| LLMS-01 | Malformed llms.txt (no H1) detected as invalid | unit | `pytest tests/test_llms.py::test_malformed_no_h1 -x` | No (Wave 0) |
| LLMS-02 | Found = score 1.0 | unit | `pytest tests/test_llms.py::test_llms_score_found -x` | No (Wave 0) |
| LLMS-02 | Not found = score 0.0 | unit | `pytest tests/test_llms.py::test_llms_score_not_found -x` | No (Wave 0) |
| LLMS-02 | Malformed but found = lower score | unit | `pytest tests/test_llms.py::test_llms_score_malformed -x` | No (Wave 0) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_robots.py tests/test_llms.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_robots.py` — all BOT-01 and BOT-02 tests
- [ ] `tests/test_llms.py` — all LLMS-01 and LLMS-02 tests
- [ ] `tests/conftest.py` — add mock robots.txt text fixtures, mock llms.txt text fixtures, mock httpx response fixtures
- [ ] No new framework installs needed (pytest already configured)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no auth in this phase |
| V3 Session Management | No | N/A — no sessions |
| V4 Access Control | No | N/A — read-only analysis |
| V5 Input Validation | Yes | robots.txt/llms.txt fetches reuse Phase 1 SSRF protection (blocked hosts + private IP ranges). URL construction for robots.txt/llms.txt paths must validate the base URL. |
| V6 Cryptography | No | N/A — no crypto operations |

### Known Threat Patterns for robots.txt/llms.txt Fetching

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via URL manipulation (e.g., input URL `http://169.254.169.254/` leading to robots.txt fetch at internal endpoint) | Spoofing | Reuse Phase 1 `is_ssrf_safe()` on the base URL before constructing robots.txt/llms.txt paths. The robots.txt path is always `/robots.txt` — never constructed from user input. |
| Response body overflow (maliciously large robots.txt) | Denial of Service | httpx streaming or content-length check. robots.txt is typically <100KB; apply a reasonable cap (e.g., 1MB). |
| Markdown injection in llms.txt content preview | Information Disclosure | Content preview is rendered as plain text, not HTML. No risk of XSS or injection. |
| Redirect to internal resource (robots.txt on external site redirects to internal IP) | Tampering | httpx `follow_redirects=True` but the redirect target should be checked against SSRF protections. If the redirect URL passes SSRF check, the response body should be size-capped. |

**Key insight:** The main security concern is SSRF via redirect chains. A seemingly valid external URL's robots.txt could redirect to an internal resource. Mitigation: after following redirects, verify the final URL passes `is_ssrf_safe()` before processing the response body.

## Sources

### Primary (HIGH confidence)
- [urllib.robotparser source code] — `/opt/miniconda3/lib/python3.13/urllib/robotparser.py` — inspected `applies_to()`, `allowance()`, `can_fetch()`, `parse()`, `RuleLine.applies_to()` methods. Confirmed substring matching bug and first-match-wins behavior. [VERIFIED: 2026-05-03]
- [llmstxt.org] — official llms.txt specification. Confirmed required structure: H1 heading (mandatory), optional blockquote, optional body text, optional H2 file-list sections. [CITED]
- [httpx official docs] — `python-httpx.org/async/` — confirmed AsyncClient pattern, single-client connection pooling, asyncio.gather usage. [CITED]
- [markdown-it-py] — version 4.0.0 confirmed installed (Rich dependency). Provides token-level markdown parsing for llms.txt validation. [VERIFIED: import check]

### Primary — AI Bot User-Agent Tokens (each verified from official source)
- **GPTBot**: `GPTBot` — OpenAI docs at `developers.openai.com/api/docs/bots` [VERIFIED]
- **ClaudeBot**: `ClaudeBot` — Anthropic support docs at `support.claude.com/en/articles/8896518` [VERIFIED]
- **PerplexityBot**: `PerplexityBot` — Perplexity docs at `docs.perplexity.ai/docs/resources/perplexity-crawlers` [VERIFIED]
- **CCBot**: `CCBot` — Common Crawl at `commoncrawl.org/ccbot` [VERIFIED]
- **Google-Extended**: `Google-Extended` — Google Crawling docs at `developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers` [VERIFIED]
- **Applebot-Extended**: `Applebot-Extended` — Apple Support at `support.apple.com/en-us/119829` [VERIFIED]
- **Amazonbot**: `Amazonbot` — Amazon dev docs at `developer.amazon.com/en-US/amazonbot` [VERIFIED]

### Primary — robots.txt Specification
- [RFC 9309] — `rfc-editor.org/rfc/rfc9309.html` — confirmed user-agent matching: case-insensitive, product token should be substring of identification string. Confirmed path matching: longest-match-wins, `*` wildcard (any sequence), `$` end anchor. [CITED]

### Secondary (MEDIUM confidence)
- [robotstxt.com/ai] — comprehensive AI bot user-agent listing. Confirmed all 7 tokens match official sources. [CITED: cross-referenced with official docs]
- [Python urllib.robotparser bugs — dev.to] — article documenting first-match-wins and longest-match issues. Used as corroboration of source code inspection findings. [CITED]
- [httpx vs ThreadPoolExecutor — StackOverflow] — community guidance on choosing between async and threaded concurrency for HTTP. [CITED: stackoverflow.com/questions/78567190]

### Tertiary (LOW confidence)
- [robotspy 0.13.0] — installed but import fails (package name mismatch). Cannot verify features. [ASSUMED: would provide RFC 9309 compliant parsing if importable]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | markdown-it-py tokenizer correctly parses all valid llms.txt markdown | llms.txt Validation | Low — markdown-it-py is CommonMark-compliant; llms.txt uses standard markdown. But if llms.txt files use non-standard markdown extensions, validation may produce false negatives. |
| A2 | llms.txt validation criteria (H1 required, H2 file lists with links) are the correct minimum bar | llms.txt Validation | Medium — the llms.txt spec is community-defined and evolving. If the spec changes to allow alternate structures, our validator would need updating. |
| A3 | robots.txt will never redirect to an internal resource (SSRF risk is theoretical) | Security Domain | Low — a redirect from `/robots.txt` to an internal IP would be malicious. Our mitigation (check final URL after redirects) covers this case regardless. |
| A4 | Scoring formula applies per-bot: if bot is in `*` catch-all group, it counts as allowed/blocked (not not_mentioned) | Scoring Logic | Medium — the scoring formula says "not_mentioned = 0.0" but doesn't clarify whether `*` catch-all counts as "mentioned." My interpretation is that `*` is a deliberate site policy that should affect the score. If the user intended that only explicit bot-by-name mentions count, the formula would need adjusting. |
| A5 | Google-Extended uses existing Googlebot UA strings in HTTP — we don't need to verify this since we only analyze robots.txt, not HTTP crawl behavior | Google-Extended | Negligible — our tool only reads robots.txt policy. The HTTP behavior is irrelevant to our analysis. |

## Open Questions

1. **llms.txt malformed score value**
   - What we know: CONTEXT.md says "Malformed but present = different score than valid and present." LLMS-02 says "found = 1.0, not found = 0.0" — binary. Malformed isn't addressed in requirements.
   - What's unclear: What exact score should a "found but malformed" llms.txt get? 0.5? 0.3? 0.0?
   - Recommendation: Propose 0.3 for malformed (present but invalid format) — it shows the site tried but got the format wrong, which is worse than not having one at all from an AI-readiness perspective. Flag for user confirmation in discuss phase.

2. **`*` catch-all = mentioned or not_mentioned?**
   - What we know: BOT-01 statuses are "allowed / blocked / not_mentioned." The `*` catch-all is a deliberate site policy.
   - What's unclear: If a bot is only covered by `*` (not by a named User-agent line), is its status "not_mentioned" (0.0) or does it inherit the `*` rule's allow/block status (with +/-0.07)?
   - Recommendation: Treat `*` catch-all as an implicit mention — the site has a policy that covers all bots. Per-bot status should be allowed or blocked based on `*` rules, earning the +/-0.07 adjustment. True "not_mentioned" (0.0) only when no rule at all applies to the bot (no matching group and no `*`). Flag for user confirmation.

3. **robots.txt size limit**
   - What we know: robots.txt is typically <100KB. The Google robots.txt spec recommends keeping it under 500KB.
   - What's unclear: What size limit should we enforce?
   - Recommendation: 1MB cap — generous enough for legit complex robots.txt files, small enough to prevent memory issues. Files exceeding this should return an error result (score 0.3, error_type='response_too_large').

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All modules | Yes | 3.13.9 | — |
| httpx | Concurrent fetch | Yes | 0.28.1 | Sequential requests (sync httpx.Client) |
| markdown-it-py | llms.txt validation | Yes | 4.0.0 | Manual regex-based H1 + link detection |
| urllib.robotparser | robots.txt parsing | Yes | stdlib 3.13 | Manual regex line-by-line parser |
| pytest | Test execution | Yes | 8.4.2 | — |

**Missing dependencies with no fallback:**
- None — all dependencies are available.

**Missing dependencies with fallback:**
- httpx is available but not declared in pyproject.toml; this is a packaging gap, not a runtime gap.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present, versions confirmed, official docs consulted
- Architecture: HIGH — urllib.robotparser source inspected, httpx async pattern confirmed, markdown-it-py API verified
- Pitfalls: HIGH — urllib.robotparser substring matching confirmed via live test, first-match-wins confirmed via source code and corroborated by external article
- AI bot tokens: HIGH — all 7 verified from official documentation sources
- llms.txt spec: MEDIUM — spec is community-defined and may evolve; validation criteria are my interpretation of the spec document
- Error taxonomy: HIGH — error classification directly derived from Phase 1 CrawlError taxonomy, extended with robots.txt-specific HTTP semantics

**Research date:** 2026-05-03
**Valid until:** 2026-07-03 (60 days — robots.txt/llms.txt specs are relatively stable but AI bot landscape may add new tokens)
