# Phase 1: Foundation — Data Contracts + Crawler - Research

**Researched:** 2026-05-03
**Domain:** Python HTTP crawling, HTML parsing, type-safe data contracts
**Confidence:** HIGH

## Summary

Phase 1 establishes the two foundational layers every downstream module depends on: (1) type-safe data contracts that define inter-module communication shapes, and (2) a URL crawler that fetches and parses HTML with realistic browser headers, automatic redirect following, and graceful error handling. The contracts are built with Python `dataclasses` — zero dependencies, runtime type-safe, and Pythonic. The crawler uses `requests` for HTTP (with a 10-second timeout, custom User-Agent, and structured error returns) and `BeautifulSoup4` with the `lxml` parser for robust HTML parsing of real-world (often malformed) markup.

The key architectural insight is that every downstream module (robots, llms.txt, schema, content) consumes HTML either as a raw string or a parsed BeautifulSoup object, and they all receive a standard `FetchResult` dataclass as their input contract. Getting the contracts right now prevents rework across the entire pipeline.

**Primary recommendation:** Build the `FetchResult` and `CrawlError` dataclasses first, then implement the crawler to produce these types. Use `lxml` parser (already installed, 6.0.2) for BeautifulSoup4 — never the default `html.parser` for production. Always pass `timeout=10` to every `requests.get()` call.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| URL validation | API / Backend | — | Input validation before any HTTP is attempted; `urllib.parse.urlsplit` with manual scheme allowlisting |
| HTTP fetching + redirects | API / Backend | — | `requests` library handles all HTTP transport, redirect following, session management |
| Error handling (timeouts, DNS, HTTP errors) | API / Backend | — | Crawler wraps all `requests` exceptions into structured `CrawlError` dicts; no browser-tier error handling |
| HTML parsing | API / Backend | — | BeautifulSoup4 with lxml parser converts raw HTML to navigable tree; happens server-side only |
| Data contract definitions | API / Backend | — | `dataclass` definitions are pure Python types consumed by all downstream backend modules |

All capabilities in this phase reside entirely in the API/Backend tier. The pipe-and-filter architecture means the crawler produces data objects that flow through four parallel analysis filters (in Phases 2-4) before converging in the scorer (Phase 5).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.33.1 (latest) / 2.32.5 (installed) | HTTP fetching with redirects, headers, timeouts | De facto standard Python HTTP library; 58k+ GitHub stars; used by every major Python web project |
| beautifulsoup4 | 4.14.3 | HTML parsing into navigable tree | The standard Python HTML parsing library; active maintenance, comprehensive documentation, mature API |
| lxml | 6.0.2 | High-performance HTML/XML parser backend for BeautifulSoup4 | Recommended by BS4 docs: "If you can, I recommend you install and use lxml for speed." Handles malformed HTML better than html.parser |
| dataclasses | stdlib (Python 3.7+) | Type-safe data contracts | Zero dependencies, built-in, Pythonic; auto-generates `__init__`, `__repr__`, `__eq__` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| urllib.parse | stdlib | URL validation via `urlsplit()` | Before every HTTP request to validate URL structure and enforce http/https scheme |
| typing | stdlib | Type annotations for contracts | On every dataclass; provides `Optional`, `List`, `Dict`, `Union` for field types |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| dataclasses | TypedDict | TypedDict is purely static-analysis only (no runtime behavior, methods, or defaults). dataclass gives real objects with `__repr__`, `__eq__`, and `__post_init__` validation. Use dataclass. |
| dataclasses | Pydantic | Pydantic adds a third-party dependency and runtime validation overhead. Overkill for internal module-to-module contracts. Use dataclass. |
| lxml parser | html.parser | html.parser ships with Python (zero install) but is slower and less lenient with malformed HTML. lxml is already installed on this system. Use lxml. |
| lxml parser | html5lib | html5lib is the most lenient parser (follows HTML5 spec) but "Very slow" per BS4 docs. Not needed for typical page analysis. Use lxml. |
| requests | httpx | httpx supports async but adds complexity. The project requirements specify synchronous, single-URL analysis. Use requests. |

**Installation:**
```bash
pip install requests beautifulsoup4 lxml
```

Note: All three are already installed on the development machine (requests 2.32.5, beautifulsoup4 4.14.3, lxml 6.0.2). requests 2.33.1 is available on PyPI — consider upgrading.

**Version verification:**
- requests: 2.33.1 latest on PyPI / 2.32.5 installed [VERIFIED: pip index]
- beautifulsoup4: 4.14.3 latest on PyPI and installed [VERIFIED: pip index]
- lxml: 6.0.2 installed [VERIFIED: python3 -c import]
- Python: 3.13.9 [VERIFIED: python3 --version] — meets 3.10+ requirement

## Architecture Patterns

### System Architecture Diagram

```
USER INPUT (URL string)
        │
        ▼
┌──────────────────────────┐
│    URL VALIDATOR          │
│  urllib.parse.urlsplit()  │
│  + scheme allowlist check │
└────────────┬─────────────┘
             │ valid URL?
             ├── NO ──▶ CrawlError (invalid_url)
             │
             ▼ YES
┌──────────────────────────┐
│    HTTP FETCHER           │
│  requests.get(            │
│    url,                   │
│    headers=REALISTIC_UA,  │
│    timeout=10,            │
│    allow_redirects=True   │
│  )                        │
└────────────┬─────────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼ Exception?    ▼ Success
┌─────────┐    ┌──────────────┐
│CrawlError│    │ Response obj │
│  dict    │    │ status, url, │
└─────────┘    │ headers,     │
               │ response.text│
               └──────┬───────┘
                      │
                      ▼
               ┌──────────────────┐
               │   HTML PARSER     │
               │ BeautifulSoup(    │
               │  response.text,   │
               │  'lxml'           │
               │ )                 │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   FetchResult     │
               │   dataclass:      │
               │  - url            │
               │  - final_url      │
               │  - status_code    │
               │  - html           │
               │  - soup (BS obj)  │
               │  - fetched_at     │
               └──────────────────┘
                        │
                        ▼
              DOWNSTREAM MODULES
              (Phases 2, 3, 4)
```

### Recommended Project Structure
```
src/
├── checker/
│   ├── __init__.py
│   ├── contracts.py      # All dataclass definitions (FetchResult, CrawlError, module contracts)
│   ├── crawler.py         # fetch_url() function — HTTP fetch + HTML parsing
│   └── exceptions.py     # Custom exception classes (if any, though CrawlError uses dict pattern)
├── tests/
│   └── test_crawler.py    # Unit tests for crawler (Wave 0)
└── pyproject.toml         # Project config + pytest settings
```

### Pattern 1: Data Contracts First (dataclass)
**What:** Define all inter-module communication shapes as frozen or mutable dataclasses in a single `contracts.py` module before writing any processing logic.
**When to use:** This phase. The `FetchResult` dataclass is the root dependency for ALL downstream modules.
**Example:**
```python
# Source: Python 3 stdlib dataclasses + pipe-and-filter pattern from
# https://dkraczkowski.github.io/articles/crafting-data-processing-pipeline/

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

@dataclass
class CrawlError:
    """Structured error result when a crawl fails."""
    url: str
    error_type: str          # 'connection_error', 'timeout', 'http_error', 'invalid_url'
    status_code: Optional[int] = None
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class FetchResult:
    """Successful crawl result with parsed HTML."""
    url: str                 # Original requested URL
    final_url: str           # URL after redirects
    status_code: int         # HTTP status code
    html: str                # Raw HTML text
    soup: BeautifulSoup      # Parsed BeautifulSoup object (lxml)
    fetched_at: datetime = field(default_factory=datetime.utcnow)
```

### Pattern 2: Defensive URL Fetch with Structured Errors
**What:** A single `fetch_url()` function that never raises — it always returns either a `FetchResult` or a `CrawlError`.
**When to use:** Every URL fetch in the system. Downstream modules should never catch HTTP exceptions.
**Example:**
```python
# Source: requests docs + project requirement CRAWL-01, CRAWL-02
# https://requests.readthedocs.io/en/latest/user/quickstart/#errors-and-exceptions

import requests
from urllib.parse import urlsplit

REALISTIC_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

def fetch_url(url: str, timeout: int = 10) -> FetchResult | CrawlError:
    # Validate URL first
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return CrawlError(url=url, error_type='invalid_url',
                         message='URL must include scheme (http/https) and hostname')
    if parsed.scheme not in ('http', 'https'):
        return CrawlError(url=url, error_type='invalid_url',
                         message=f'Scheme "{parsed.scheme}" not supported. Use http or https.')

    try:
        response = requests.get(
            url,
            headers=REALISTIC_HEADERS,
            timeout=timeout,
            allow_redirects=True
        )
        # Check for HTTP errors (4xx, 5xx)
        if not response.ok:
            return CrawlError(
                url=url,
                error_type='http_error',
                status_code=response.status_code,
                message=f'HTTP {response.status_code} for url: {url}'
            )

        soup = BeautifulSoup(response.text, 'lxml')
        return FetchResult(
            url=url,
            final_url=response.url,
            status_code=response.status_code,
            html=response.text,
            soup=soup
        )

    except requests.exceptions.Timeout:
        return CrawlError(url=url, error_type='timeout',
                         message=f'Request timed out after {timeout}s: {url}')
    except requests.exceptions.ConnectionError:
        return CrawlError(url=url, error_type='connection_error',
                         message=f'Connection failed (DNS, refused, or network issue): {url}')
    except requests.exceptions.TooManyRedirects:
        return CrawlError(url=url, error_type='too_many_redirects',
                         message=f'Too many redirects for url: {url}')
    except requests.exceptions.RequestException as e:
        return CrawlError(url=url, error_type='request_error',
                         message=f'Unexpected request error: {str(e)}')
```

### Pattern 3: Contract-Driven Module Interface
**What:** Every phase defines its output contract in `contracts.py` first. Downstream phases accept these contracts as typed inputs.
**When to use:** This phase and every subsequent phase. All four analysis modules (Phases 2-4) will accept `FetchResult` as input.
**Example:**
```python
# contracts.py defines SHAPES. Each downstream module uses them.
# Phase 2 example (for reference; not built in Phase 1):

# def analyze_robots(fetch_result: FetchResult) -> RobotsAnalysis:
#     """Downstream module accepts the contract from Phase 1."""
#     ...
```

### Anti-Patterns to Avoid
- **Returning raw `Response` objects:** Downstream modules should never touch `requests.Response` directly. Always wrap in `FetchResult` so the HTTP library is an implementation detail.
- **Letting exceptions propagate:** The contract with downstream modules is "always return a result dict." Raising exceptions forces every consumer to duplicate error handling.
- **Using `html.parser` in production:** It fails silently on malformed HTML and is slower. Always use `lxml` when available (it is).
- **Omitting timeout:** `requests.get(url)` without `timeout=` hangs indefinitely on unresponsive servers. Always pass `timeout=10`.
- **Accessing BeautifulSoup results without None checks:** `.find()` and `.find_all()` return `None` when nothing matches. Always guard with `if result:` before accessing attributes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client with redirects, gzip, connection pooling | Custom `http.client` or `urllib.request` code | `requests` | Handles redirects, gzip/deflate/brotli decoding, connection pooling, cookie jars, SSL verification — years of edge case fixes you'd have to rediscover |
| URL parsing and validation | Regex-based URL matching | `urllib.parse.urlsplit()` | URLs are deceptively complex (IP vs hostname, punycode, port, auth, fragments). Standard library is battle-tested |
| HTML parsing | Regex on raw HTML | BeautifulSoup4 with lxml | Regex cannot correctly parse HTML (nesting, malformed tags, comments). BeautifulSoup handles real-world markup that regex would silently misparse |
| Type-safe data objects | Dict with convention-based keys | `dataclass` | Typo in a dict key is a silent bug; dataclass field access is checked by IDE/mypy at dev time |
| Retry logic for transient failures | Manual retry loop with `time.sleep()` | Built into requests (for redirects only). For transient network errors in v1: explicit `fetch_url()` returns `CrawlError` — caller decides to retry | |

**Key insight:** The "don't hand-roll" principle applies most strongly to HTML parsing. Novices often try regex-based HTML extraction. Every experienced developer learns this is a dead end — HTML's nesting and optional closing tags break all regex approaches. BeautifulSoup4 exists specifically because this problem is harder than it looks.

## Runtime State Inventory

> This section is for rename/refactor/migration phases only. This is a greenfield Phase 1 — no runtime state exists to inventory.

**Skipped.** No data stores, live services, OS-registered state, secrets, or build artifacts exist for this project yet.

## Common Pitfalls

### Pitfall 1: Encoding Mismatch Corruption
**What goes wrong:** Characters display as garbled text (mojibake) because the server sends content in Latin-1 but requests auto-detects UTF-8, or vice versa.
**Why it happens:** `response.text` guesses encoding from HTTP headers, which can be wrong. HTML documents often declare their own encoding in `<meta charset>` tags that contradict the HTTP header.
**How to avoid:** Pass `response.content` (raw bytes) to BeautifulSoup4, which has its own encoding detection that reads `<meta>` tags and byte-order marks. BS4's `UnicodeDammit` handles this better than requests alone.
**Warning signs:** Strange characters replacing apostrophes, quotes, em-dashes, or non-ASCII text.

```python
# RIGHT: Let BeautifulSoup handle encoding
soup = BeautifulSoup(response.content, 'lxml')

# WRONG: Trust requests' auto-detection blindly
soup = BeautifulSoup(response.text, 'lxml')
```

### Pitfall 2: Unspecified Parser Leads to Inconsistent Behavior
**What goes wrong:** Code works on your machine (where lxml is installed) but breaks or produces different results on another machine (where only html.parser is available).
**Why it happens:** BeautifulSoup auto-selects a parser based on what's installed: lxml > html5lib > html.parser. Different parsers produce different parse trees from the same malformed HTML.
**How to avoid:** ALWAYS specify the parser explicitly: `BeautifulSoup(html, 'lxml')`. Never rely on auto-detection.
**Warning signs:** Tests pass locally but fail in CI. Parse tree structure differs between environments.

### Pitfall 3: Timeout Not Applied → Indefinite Hang
**What goes wrong:** A single slow or unresponsive server causes the entire program to hang with no feedback.
**Why it happens:** `requests.get(url)` has no default timeout. Without `timeout=`, the call blocks forever waiting for a response that may never come.
**How to avoid:** Always pass `timeout=10` to every `requests.get()` call. The requirement explicitly specifies 10-second timeout.
**Warning signs:** Program appears frozen with no output. No exception is raised — it simply waits.

### Pitfall 4: String vs Bytes Confusion with BeautifulSoup
**What goes wrong:** `soup.find('p').string` returns `None` when you expected text, because the tag has multiple children.
**Why it happens:** `.string` only works when a tag has exactly one child that is a `NavigableString`. For tags with multiple children or nested tags, it returns `None`.
**How to avoid:** Use `.get_text()` (or the `.text` property) instead of `.string` for extracting all text from a tag and its descendants.
**Warning signs:** Silent `None` values where text was expected; `AttributeError` on subsequent `.strip()` call.

### Pitfall 5: URL Validation Gap
**What goes wrong:** Passing `"example.com"` (no scheme) to `requests.get()` causes a cryptic `MissingSchema` error, or passing `"file:///etc/passwd"` (wrong scheme) could cause unexpected behavior.
**Why it happens:** `requests` assumes `http://` if no scheme is present (in some versions), or raises an unhelpful error. Non-http schemes may trigger dangerous local file access.
**How to avoid:** Validate with `urlsplit()` before the HTTP call. Require both `scheme` and `netloc` to be present. Allowlist schemes to `http` and `https` only.
**Warning signs:** Cryptic `requests.exceptions.MissingSchema` or `InvalidSchema` errors.

## Code Examples

Verified patterns from official sources:

### Fetch with Redirects, Headers, and Timeout
```python
# Source: https://requests.readthedocs.io/en/latest/user/quickstart/
# Verified with Context7: /websites/requests_readthedocs_io_en

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}

r = requests.get('http://github.com/', headers=headers, timeout=10)
# r.status_code -> 200
# r.url -> 'https://github.com/'  (followed redirect)
# r.history -> [<Response [301]>]  (redirect chain)
```

### Parse HTML with BeautifulSoup4 + lxml
```python
# Source: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
# Verified with Context7: /websites/crummy_software_beautifulsoup_bs4_doc

from bs4 import BeautifulSoup

soup = BeautifulSoup(response.content, 'lxml')  # Always specify parser
# soup.find('title').get_text() -> page title
# soup.select('a[href]') -> all links with href
```

### Graceful Error Handling Pattern
```python
# Source: https://requests.readthedocs.io/en/latest/user/quickstart/#errors-and-exceptions
# Verified with Context7: /websites/requests_readthedocs_io_en

try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
except requests.exceptions.Timeout:
    # Handle timeout
except requests.exceptions.ConnectionError:
    # Handle DNS/network failure
except requests.exceptions.HTTPError:
    # Handle 4xx/5xx
except requests.exceptions.RequestException:
    # Catch-all for any other requests error
```

### URL Validation
```python
# Source: https://docs.python.org/3/library/urllib.parse.html
# Note: urlsplit does NOT validate — you must check scheme and netloc manually

from urllib.parse import urlsplit

def is_valid_http_url(url: str) -> bool:
    result = urlsplit(url)
    return (result.scheme in ('http', 'https')
            and bool(result.netloc)
            and '.' in result.netloc)  # Basic netloc sanity check
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `urllib.request` for HTTP | `requests` library | ~2011 | Simpler API, automatic redirect/gzip handling |
| `html.parser` default | `lxml` specified explicitly | Ongoing best practice | Faster parsing, better malformed HTML handling |
| Dict-based contracts | `dataclass` with type annotations | Python 3.7 (2018) | Type safety, IDE support, `__post_init__` validation |
| Try/except at call sites | Structured return type (`FetchResult | CrawlError`) | Pattern established in Rust/Go, adopted in Python | Callers handle errors explicitly without try/except |

**Deprecated/outdated:**
- `urlparse()` (with `params`): Use `urlsplit()` instead. The docs say `urlsplit()` "should generally be used instead of `urlparse()`" since the params/path split is based on obsolete RFCs.
- `response.text` for HTML parsing: Prefer `response.content` — pass raw bytes to BeautifulSoup's `UnicodeDammit` for better encoding detection.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The project will use `dataclass` rather than `TypedDict` for data contracts | Standard Stack, Architecture Patterns | TypedDict would still work but would lose runtime repr, equality, and `__post_init__` validation. Low risk — either pattern is valid and the contracts have the same shape. |
| A2 | lxml 6.0.2 will remain the recommended parser for the project's lifetime | Common Pitfalls | If a future Python version breaks lxml's C extension, we'd need to fall back to html.parser. Low risk — lxml is actively maintained and widely used. |
| A3 | The `contracts.py` module will define ALL phase contracts (not just Phase 1) | Architecture Patterns | If contracts are scattered across modules, the planner for future phases will need to locate them. Medium risk — the plan should explicitly note that `contracts.py` is the single source of truth. |
| A4 | `FetchResult.soup` (BeautifulSoup object) is an appropriate field for a dataclass | Architecture Patterns | BeautifulSoup objects are large and non-serializable. If the contract needs to be serialized (JSON, pickle), this field would need to be excluded. Medium risk — Phase 5 report generation may need serialization; if so, remove `soup` from the contract and pass it separately. |

## Open Questions (RESOLVED)

1. **RESOLVED: Should `FetchResult` include a parsed BeautifulSoup object, or just raw HTML?**
   - What we know: Both Phase 3 (schema) and Phase 4 (content) need parsed HTML. Caching the parsed tree avoids re-parsing.
   - What's unclear: Whether the BeautifulSoup object should live in the contract or be created on-demand by each module. BS objects are stateful and not pickle-serializable.
   - **RESOLVED:** Include `soup` in `FetchResult`. It's the pragmatic choice — all four downstream modules need it. If serialization becomes necessary (Phase 5 report), the scorer can work with the raw `html` field.

2. **RESOLVED: What User-Agent string should be the "realistic browser header"?**
   - What we know: The requirement says "realistic browser headers." The most common pattern is a recent Chrome User-Agent string.
   - What's unclear: Whether the User-Agent should be configurable, whether there should be rotation, or whether a single fixed string is sufficient.
   - **RESOLVED:** Use a single Chrome 131 User-Agent string (latest stable as of research). Make it a module-level constant for easy replacement. No rotation needed for single-URL analysis.

3. **RESOLVED: Should the crawler include response header metadata in FetchResult?**
   - What we know: v2 requirement CRAWL-03 asks for "response metadata (final URL after redirects, status code, headers)." Headers are the only piece not in the current FetchResult.
   - What's unclear: Whether to include headers now (forward-looking) or add in v2.
   - **RESOLVED:** Include `final_url` and `status_code` (needed for v1). Skip `headers` for now — they are a v2 requirement. Add a `# TODO: v2 — add response.headers dict` comment.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Entire project | Yes | 3.13.9 | — |
| requests | HTTP fetching | Yes | 2.32.5 (2.33.1 available) | — |
| beautifulsoup4 | HTML parsing | Yes | 4.14.3 | — |
| lxml | Fast HTML parser for BS4 | Yes | 6.0.2 | — |
| pip | Package installation | Yes | Bundled with Python | — |
| pytest | Testing (Wave 0) | Yes | 8.4.2 | — |

**Missing dependencies with no fallback:** None. All core dependencies are already installed.

**Missing dependencies with fallback:**
- requests 2.32.5 installed vs 2.33.1 available on PyPI: Optional upgrade. No breaking changes in 2.33.x relevant to this phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | pyproject.toml (needs `[tool.pytest.ini_options]` section) |
| Quick run command | `pytest tests/test_crawler.py -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRAWL-01 | Valid URL returns FetchResult with parsed HTML, realistic headers, redirect following | integration | `pytest tests/test_crawler.py::test_fetch_url_success -x` | No (Wave 0) |
| CRAWL-01 | Redirect chain is followed and final_url reflects destination | unit | `pytest tests/test_crawler.py::test_follows_redirects -x` | No (Wave 0) |
| CRAWL-02 | Connection error returns CrawlError, not exception | unit | `pytest tests/test_crawler.py::test_connection_error_returns_crawlerror -x` | No (Wave 0) |
| CRAWL-02 | Timeout returns CrawlError with error_type='timeout' | unit | `pytest tests/test_crawler.py::test_timeout_returns_crawlerror -x` | No (Wave 0) |
| CRAWL-02 | HTTP 4xx/5xx returns CrawlError with error_type='http_error' | unit | `pytest tests/test_crawler.py::test_http_error_returns_crawlerror -x` | No (Wave 0) |
| CRAWL-02 | Invalid URL returns CrawlError with error_type='invalid_url' | unit | `pytest tests/test_crawler.py::test_invalid_url_returns_crawlerror -x` | No (Wave 0) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_crawler.py -v`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_crawler.py` — covers all CRAWL-01 and CRAWL-02 behaviors
- [ ] `tests/conftest.py` — shared fixtures (mock responses, test URLs)
- [ ] `pyproject.toml` — add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`
- [ ] Test infrastructure install: pytest already available (8.4.2)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — (no user accounts or auth in this phase) |
| V3 Session Management | No | — (stateless crawler) |
| V4 Access Control | No | — (no protected resources) |
| V5 Input Validation | Yes | `urllib.parse.urlsplit()` with scheme allowlist (`http`, `https` only) |
| V6 Cryptography | No | — (TLS handled by requests/urllib3 automatically) |

### Known Threat Patterns for Python HTTP Crawler

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Server-Side Request Forgery (SSRF) via malicious URL | Spoofing | Scheme allowlist (`http`/`https` only); reject `file://`, `ftp://`, `gopher://`; validate netloc is not localhost/127.0.0.1/169.254.x.x |
| XML External Entity (XXE) via malicious HTML | Tampering | `lxml` disables XXE by default in modern versions; verify with `lxml>=4.9` |
| Billion Laughs / decompression bomb via large HTML | Denial of Service | Set `response.content` size limit; reject responses over configurable threshold (e.g., 10MB) |
| Malformed HTML crash via parser DoS | Denial of Service | `lxml` handles most malformed HTML gracefully; wrap parsing in try/except as safety net |
| User-Agent forgery (pretending to be the tool) | Spoofing | Use realistic but identifiable User-Agent; consider adding `X-Tool: ai-readiness-checker` custom header |

### SSRF Prevention (Critical)

The crawler accepts arbitrary URLs from users. This makes SSRF the highest-priority security concern:

```python
# REQUIRED: SSRF prevention via scheme + host allow/denylist
from urllib.parse import urlsplit
import ipaddress

BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
BLOCKED_NETWORKS = ['169.254.0.0/16', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']

def is_ssrf_safe(url: str) -> bool:
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    hostname = parsed.hostname or ''
    if hostname.lower() in BLOCKED_HOSTS:
        return False
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            return False
    except ValueError:
        pass  # Not an IP address, proceed
    return True
```

This is not a `[ASSUMED]` claim — SSRF prevention is a standard requirement for any tool that fetches arbitrary URLs [CITED: OWASP ASVS V5.1.1]. The specific allowlist/denylist approach is the recognized best practice.

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/requests_readthedocs_io_en` — Requests library: exception hierarchy, Response object attributes, error handling, timeout behavior, redirect following, custom headers
- Context7 `/websites/crummy_software_beautifulsoup_bs4_doc` — BeautifulSoup4: parser specification, parser differences, HTML parsing from string, finding elements, CSS selectors
- Official requests docs: https://requests.readthedocs.io/en/latest/user/quickstart/ — Quickstart guide covering all major features
- Official BeautifulSoup4 docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/ — Complete documentation, parser comparison table
- Official Python docs: https://docs.python.org/3/library/urllib.parse.html — urlsplit(), URL parsing functions, validation caveats
- PyPI: pip index requests (2.33.1 latest), pip index beautifulsoup4 (4.14.3 latest)

### Secondary (MEDIUM confidence)
- pytutorial.com — BeautifulSoup4 common errors and troubleshooting guide (cross-referenced with official BS4 docs)
- Pipe-and-filter architecture article: https://dkraczkowski.github.io/articles/crafting-data-processing-pipeline/ — Protocol-based pipeline pattern with dataclass contracts

### Tertiary (LOW confidence)
- None. All findings were verified against official documentation or PyPI.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries verified against PyPI and official docs; versions confirmed installed
- Architecture: HIGH — Pipe-and-filter pattern well-documented; dataclass contracts are a standard Python pattern
- Pitfalls: HIGH — Pitfalls cross-referenced with official docs, Context7, and community troubleshooting guides
- Security: HIGH — SSRF prevention based on OWASP ASVS V5.1.1; lxml XXE behavior verified against project documentation

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days; all libraries in this stack are stable and mature)
