# Pitfalls Research

**Domain:** Python web scraping + NLP scoring tool (AI Readiness Checker)
**Researched:** 2026-05-02
**Confidence:** HIGH (library-specific issues verified via official GitHub issues and documentation)

---

## Critical Pitfalls

### Pitfall 1: requests sends "python-requests/X.X" as User-Agent — instant block on many sites

**What goes wrong:**
The `requests` library defaults to `User-Agent: python-requests/2.x.x`. Most CDN-level bot detection systems (Cloudflare, Akamai, Fastly) treat this as a guaranteed bot signal and return a 403, a CAPTCHA redirect, or a 200 with empty/fake content — with no exception raised. The crawl silently "succeeds" but the HTML body contains a block page, not the real page.

**Why it happens:**
`requests.get(url)` sends exactly one User-Agent header. Developers test against cooperative sites first, don't notice the default, and only discover the problem when they hit a real-world e-commerce site.

**How to avoid:**
Set a realistic browser User-Agent on every request, plus the full set of headers a browser sends (Accept, Accept-Language, Accept-Encoding). Specifically:
```python
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
}
```
Do NOT strip `Accept-Encoding` — removing it is itself a bot signal. Let `requests` decompress transparently.

**Warning signs:**
- Response body is less than ~5KB for a site that should have product/schema content
- Body contains words like "Access Denied", "checking your browser", "enable JavaScript"
- `response.status_code == 200` but `len(response.text) < 2000`

**Phase to address:**
Crawler module (Module 1). Define a shared `HEADERS` constant in `crawler.py`; all `requests.get()` calls use it.

---

### Pitfall 2: extruct raises unhandled exceptions on malformed JSON-LD (common on real CMS platforms)

**What goes wrong:**
`extruct.extract()` calls `json.loads()` internally on every `<script type="application/ld+json">` block it finds. Real sites frequently have:
- Trailing semicolons after the closing `}` (common in Shopify themes)
- Extra/unclosed braces (WordPress Yoast plugin has known malformed output)
- HTML entities inside the JSON string (`&amp;` instead of `&`)
- Empty `<script type="application/ld+json"></script>` blocks

Any of these raises `json.JSONDecodeError` (or `ValueError`) inside extruct and bubbles up uncaught, **crashing the entire analysis pipeline** for that URL.

**Why it happens:**
`extruct.extract()` has no `errors='ignore'` option. The `uniform=True` flag normalizes structure but does not add error tolerance. Developers assume JSON-LD in the wild is valid JSON; it frequently is not.

**How to avoid:**
Wrap the `extruct.extract()` call in a broad try/except and return an empty result on failure:
```python
try:
    data = extruct.extract(html, base_url=url, syntaxes=["json-ld", "microdata", "opengraph"])
except Exception:
    data = {"json-ld": [], "microdata": [], "opengraph": []}
```
Additionally, validate each extracted JSON-LD item individually rather than trusting the batch result.

**Warning signs:**
- `JSONDecodeError` or `ValueError` stack traces during manual testing on Shopify/WooCommerce sites
- `extruct.extract()` returns empty for a site that Google Search Console shows as having rich results

**Phase to address:**
Schema extraction module (Module 4). The try/except wrapper must be in place before any real-world URL is tested.

---

### Pitfall 3: spaCy raises ValueError on long pages (default max_length is 1,000,000 characters)

**What goes wrong:**
spaCy's `nlp()` call enforces a hard character limit (default: 1,000,000 characters). Large e-commerce homepages with embedded JSON blobs, minified JS, or inline SVGs can exceed this. The error is `ValueError: [E088] Text of length X exceeds maximum of 1000000`. More dangerously: passing raw HTML (including `<script>` tags) to spaCy instead of extracted text will inflate character count massively and pollute entity detection with JavaScript tokens.

**Why it happens:**
Developers often pass `response.text` (raw HTML) to `nlp()` instead of BeautifulSoup-extracted visible text. Even with text extraction, pages with deeply nested content can be large.

**How to avoid:**
1. Always extract visible text with BeautifulSoup before calling spaCy:
   ```python
   for tag in soup(["script", "style", "noscript"]):
       tag.decompose()
   text = soup.get_text(separator=" ", strip=True)
   ```
2. Truncate text before passing to spaCy — for this use case (single-page analysis), 50,000 characters is more than sufficient for readability and entity detection:
   ```python
   text = text[:50000]
   ```
3. Disable unused pipeline components to speed up processing:
   ```python
   nlp = spacy.load("en_core_web_sm", disable=["parser"])
   ```

**Warning signs:**
- `ValueError: [E088]` crash during testing on content-heavy pages
- spaCy processing time exceeds 5 seconds on a single page (sign of processing script/style noise)
- Entity results include tokens like `var`, `function`, `const` (raw JS leaking through)

**Phase to address:**
Content analysis module (Module 5). Text cleaning must happen before any NLP call.

---

### Pitfall 4: textstat returns nonsensical scores for very short or non-English text

**What goes wrong:**
`textstat` functions like `flesch_reading_ease()` are calibrated for multi-sentence English prose. They produce garbage output for:
- Pages with fewer than ~100 words (single product title + SKU + price)
- Non-English text (score goes wildly out of expected range)
- Text that is mostly numbers, URLs, or code snippets
- Empty strings (raises `ZeroDivisionError` in syllable counting)

A Flesch score of -200 or a reading grade of 99 will propagate directly into your weighted final score and produce a misleading A or F grade for the whole page.

**Why it happens:**
`textstat` does not validate its input. It computes averages over sentences and syllables; if either count is zero the division fails silently or raises. Developers test on normal English paragraphs and don't exercise the edge cases.

**How to avoid:**
Guard every `textstat` call:
```python
word_count = textstat.lexicon_count(text, removepunct=True)
if word_count < 50:
    readability_score = None  # insufficient content to score
else:
    raw = textstat.flesch_reading_ease(text)
    readability_score = max(0.0, min(100.0, raw))  # clamp to 0-100
```
Return `None` (not `0`) for insufficient-content cases. The scorer must handle `None` sub-scores without treating them as zeros.

**Warning signs:**
- Flesch scores below -50 or above 120 in test runs
- `ZeroDivisionError` on pages with only a title and navigation text
- Final weighted scores that swing wildly for thin-content pages

**Phase to address:**
Content analysis module (Module 5) for the guard logic; Scorer module (Module 6) for `None`-safe weighted aggregation.

---

### Pitfall 5: Weighted scorer divides by zero or produces scores outside 0–100 when sub-scores are missing

**What goes wrong:**
The final score is a weighted average of four module scores. If one module fails (network error fetching robots.txt, extruct crash, spaCy error) and returns `None` instead of a numeric score, the weighted sum silently becomes `NaN` or the weights no longer sum to 1.0 — producing a score of `None`, `nan`, or a value like `0.7` when the scale is meant to be 0–100.

**Why it happens:**
Naive implementation: `score = 0.20*robots + 0.15*llms + 0.30*schema + 0.35*content`. If any term is `None`, Python raises `TypeError`. If the developer uses `or 0` as a fallback, missing modules artificially drag the score down.

**How to avoid:**
Re-weight dynamically around available scores:
```python
weights = {"robots": 0.20, "llms": 0.15, "schema": 0.30, "content": 0.35}
scores = {"robots": robots_score, "llms": llms_score, ...}  # each is float or None
available = {k: v for k, v in scores.items() if v is not None}
total_weight = sum(weights[k] for k in available)
if total_weight == 0:
    final_score = None
else:
    final_score = sum(weights[k] * available[k] for k in available) / total_weight
```
Always clamp the final result: `final_score = max(0.0, min(100.0, final_score))`.

**Warning signs:**
- `TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'` in the scorer
- Final score of exactly `0.0` for sites where only one module failed
- Grade shows `A` for a site that is clearly not AI-ready (unclamped score above 100)

**Phase to address:**
Scorer module (Module 6). This is the integration point for all sub-scores and must be built with these edge cases as first-class requirements.

---

### Pitfall 6: Streamlit reruns the entire script on every interaction — slow pipeline runs on every widget change

**What goes wrong:**
Streamlit re-executes the full Python script top-to-bottom every time the user interacts with any widget (button click, tab switch, expander open). Without caching, the full crawl + extruct + spaCy pipeline re-runs on every interaction — 5–15 second delays on each click. Users think the app is broken.

**Why it happens:**
Streamlit's execution model is stateless by default. Developers build the pipeline inline without `@st.cache_data` and only notice the performance problem after the UI is complete.

**How to avoid:**
Wrap the analysis pipeline in a single `@st.cache_data` function keyed on the URL:
```python
@st.cache_data(ttl=300, show_spinner=False)
def run_analysis(url: str) -> dict:
    # all modules run here
    ...
```
Use `st.spinner()` to provide feedback during the first run. After the first analysis, all UI interactions (expanding sections, switching tabs) are instant because the result is cached. Set `ttl=300` (5 minutes) so users can re-analyze after fixing their site.

Note: `@st.cache_resource` is for shared objects (the spaCy model); `@st.cache_data` is for per-URL results. Use the right one for the right thing.

**Warning signs:**
- Analysis runs again when you expand an accordion or click a tab
- Streamlit spinner appears for non-analysis actions
- Multiple HTTP requests to the same URL visible in network logs during one "session"

**Phase to address:**
Streamlit module (Module 8). spaCy model loading should also be wrapped in `@st.cache_resource` to avoid reloading the model on every rerun.

---

### Pitfall 7: urllib.robotparser does not implement RFC 9309 — longest-match rule and wildcards silently misfire

**What goes wrong:**
Python's stdlib `urllib.robotparser` is based on the original 1997 robots.txt specification, not the current RFC 9309. It uses first-match semantics instead of longest-match, and does not support `*` or `$` wildcards in Allow/Disallow directives. This means:
- `Disallow: /` + `Allow: /products/` — `RobotFileParser` may incorrectly report `/products/page` as disallowed
- `Disallow: /*.pdf$` — the `$` anchor is ignored entirely; all PDFs appear allowed
- Crawl-delay with invalid syntax returns `None` silently

For the AI Readiness Checker, this is a scoring risk: the tool may report "AI bots blocked" when they aren't, or "allowed" when they're blocked.

**Why it happens:**
`urllib.robotparser` is part of the standard library and developers assume it is spec-compliant. The gaps are not obvious from the docstring.

**How to avoid:**
Parse robots.txt manually using `response.text.splitlines()` for the specific bot names this tool checks (GPTBot, ClaudeBot, etc.) rather than relying on `RobotFileParser.can_fetch()`. A targeted line-by-line scan for each bot agent is simpler and more reliable for this use case than a full robots.txt parser. Alternatively, use the `robotspy` package which implements RFC 9309.

**Warning signs:**
- `can_fetch("GPTBot", url)` returns `True` for a site with `User-agent: * / Disallow: /`
- Results differ from Google's Rich Results Test robots.txt interpretation
- Sites with wildcard rules produce inconsistent allow/block results

**Phase to address:**
Robots module (Module 2). Parse the relevant bot-name sections directly rather than delegating to `RobotFileParser`.

---

### Pitfall 8: BeautifulSoup encoding detection is slow and sometimes wrong — garbled characters in NLP text

**What goes wrong:**
BeautifulSoup uses `chardet` (pure Python) to auto-detect character encoding when the Content-Type header is missing or declares `charset=utf-8` incorrectly. On pages with high-UTF-8-but-declared-as-Latin-1 content (common on legacy e-commerce sites), chardet guesses wrong and the extracted text contains mojibake (`Ã©` instead of `é`). This is invisible — no exception, no warning — but spaCy and textstat will produce incorrect results on the garbled text.

Additionally, `chardet` adds 200–800ms latency on large pages because it reads the full byte string before parsing begins.

**Why it happens:**
Developers pass `response.text` (which `requests` has already decoded using its own charset detection) to BeautifulSoup. But `requests` charset detection is also imperfect — it reads the `Content-Type` header only, not the meta charset tag inside the HTML.

**How to avoid:**
Pass `response.content` (raw bytes) to BeautifulSoup, specifying `lxml` as the parser, and let BeautifulSoup handle encoding from the meta tag + byte detection:
```python
soup = BeautifulSoup(response.content, "lxml")
```
Not `response.text`. The `lxml` parser is significantly faster than `html.parser` and handles malformed HTML better. Install `cchardet` as a drop-in faster replacement for `chardet` — it reduces encoding detection time by ~10x.

**Warning signs:**
- Extracted text contains sequences like `Ã`, `â€`, `Â` (Latin-1 mojibake of UTF-8)
- Entity detection returns garbled tokens
- Parsing a single large page takes more than 1 second (chardet bottleneck)

**Phase to address:**
Crawler module (Module 1). The `BeautifulSoup(response.content, "lxml")` pattern must be established as the baseline before any downstream modules are built.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `response.text` instead of `response.content` for BeautifulSoup | One less line of code | Mojibake on non-UTF-8 sites, wrong entity extraction | Never |
| Skipping the try/except around `extruct.extract()` | Simpler code | Pipeline crashes on any Shopify/WooCommerce site | Never |
| Using `textstat` score of `0` for None/missing content | Simpler scorer | Thin pages always fail, misleading grades | Never — use `None` and re-weight |
| Loading spaCy model at module level without `@st.cache_resource` | Slightly less code | Model reloads on every Streamlit rerun (~1–2s) | Never in Streamlit context |
| Skipping clamping on sub-scores | Simpler code | Scores above 100 or below 0 produce invalid grades | Never |
| Hard-coding `allow_redirects=True` without a redirect limit | Simpler code | Infinite redirect loops hang the app | Acceptable to set `max_redirects=5` in requests Session |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `extruct` + real sites | Calling without try/except, assuming valid JSON-LD | Wrap in broad `except Exception`, return empty dict per syntax |
| `spaCy` + web text | Passing raw HTML or full `response.text` to `nlp()` | Strip tags with BeautifulSoup first, truncate to 50K chars |
| `textstat` + short pages | Calling `flesch_reading_ease()` on <50-word text | Guard with `lexicon_count()` check, return `None` if insufficient |
| `urllib.robotparser` + modern robots.txt | Using `can_fetch()` to check GPTBot/ClaudeBot | Parse the raw file line-by-line for specific agent names |
| `streamlit` + slow pipeline | Running analysis in script body without caching | `@st.cache_data(ttl=300)` wrapping the entire pipeline |
| `requests` + redirects | Not checking final URL after redirect chain | Inspect `response.url` to detect unexpected domain changes or login pages |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading spaCy model on every Streamlit rerun | 2s startup time on every widget interaction | `@st.cache_resource` for `spacy.load()` | Immediately on first real UI interaction |
| `chardet` encoding detection on large HTML | 800ms+ per page for encoding detection alone | Install `cchardet`; use `lxml` parser | Pages over ~100KB |
| Running extruct with all syntaxes enabled on pages with heavy RDFa | 5–10s extraction time for RDFa-heavy pages | Limit `syntaxes=["json-ld", "microdata", "opengraph"]` — skip `rdfa` and `dublincore` unless needed | Any enterprise CMS with RDFa |
| spaCy running full pipeline (parser + NER + tagger) when only NER is needed | 2–3x slower processing | `disable=["parser", "tagger"]` when only `doc.ents` is needed | Any page over 10K characters |
| No timeout on `requests.get()` | App hangs indefinitely on slow sites | Always set `timeout=(5, 15)` — 5s connect, 15s read | Any site over 10s response time |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Setting `verify=False` on SSL errors | Silences legitimate errors, masks MITM risk, unsafe to ship as open-source tool | Catch `SSLError` explicitly, report it as a fetch failure in the score report, never disable verification |
| Following redirects to any domain without checking | User inputs `goodsite.com`, which redirects to a phishing page; tool crawls attacker content | Check `response.url` domain matches input domain after redirect; warn if domain changes |
| Passing unsanitized user URL directly to `requests.get()` | `file://`, `ftp://`, or `http://internal-host` SSRF | Validate URL scheme is `http` or `https` before any request |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing only the final score with no intermediate feedback | 10–15 second blank screen looks broken | Use `st.status()` or progressive `st.write()` updates per module as they complete |
| Displaying raw score numbers without context (e.g., "74.2") | User doesn't know if 74.2 is good | Show A–F grade badge prominently; show comparison like "30 points from an A" |
| Crashing with a Python traceback on fetch failure | Users with blocked/slow sites see a stack trace | Catch all fetch and parsing errors; show a clean "Could not analyze this site: [reason]" message |
| No explanation for why extruct returned empty schema | User thinks their schema is missing when it may have been malformed | Distinguish between "no schema found" and "schema found but could not be parsed" in the report |
| Spinner with no elapsed time indicator | Users abandon after ~10 seconds of no feedback | Use `st.spinner()` with `show_time=True` (available in Streamlit 2025 releases) |

---

## "Looks Done But Isn't" Checklist

- [ ] **Crawler:** Test against a Shopify store, a WordPress/WooCommerce site, and a Cloudflare-protected site — not just plain HTML pages. Verify `response.url` is inspected after redirects.
- [ ] **robots.txt parser:** Test against a robots.txt with `Allow:` rules that override a broader `Disallow:`, and one with `*` wildcards. Verify GPTBot/ClaudeBot detection is not relying solely on `can_fetch()`.
- [ ] **extruct module:** Test against a site with malformed JSON-LD (add a trailing semicolon to a test fixture). Verify the pipeline does not crash — it returns an empty schema score.
- [ ] **spaCy text prep:** Verify that `<script>` and `<style>` tags are stripped before NLP. Check that entity results contain real entities, not JS tokens.
- [ ] **textstat guards:** Test with a 10-word page, a 0-word page, and an empty string. Verify no `ZeroDivisionError` and that scores return `None` rather than `0`.
- [ ] **Scorer:** Test with one sub-score as `None`. Verify the final score re-weights correctly and stays in 0–100 range.
- [ ] **Streamlit:** Open the app and click through all expanders and tabs after an analysis. Verify the pipeline does not re-run. Verify the spaCy model is not reloaded on each interaction.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Bot detection blocking analysis | LOW | Add/update headers in `crawler.py`; no other modules affected |
| extruct crash propagating through pipeline | MEDIUM | Add try/except in schema module; re-test all schema scoring logic |
| spaCy max_length crash | LOW | Add truncation and HTML stripping in content module text prep function |
| textstat ZeroDivisionError cascade | MEDIUM | Add guards per metric; audit scorer for `None` handling simultaneously |
| Scorer returning NaN due to None sub-scores | MEDIUM | Rewrite weighted aggregation to re-weight dynamically; re-test all grade thresholds |
| Streamlit full pipeline rerun on every click | LOW | Wrap pipeline in `@st.cache_data`; no logic changes needed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Default User-Agent blocking | Module 1: Crawler | Test against cloudflare-protected URL; assert body length > 5KB and no "Access Denied" |
| extruct malformed JSON-LD crash | Module 4: Schema extraction | Test fixture with semicolon-terminated JSON-LD; verify no exception raised |
| spaCy max_length / HTML noise | Module 5: Content analysis | Test with page containing inline JS; verify entity list contains no JS tokens |
| textstat on thin/empty content | Module 5: Content analysis | Test with 0-word, 10-word, 100-word inputs; verify no ZeroDivisionError |
| Scorer None/NaN/out-of-range | Module 6: Scorer | Unit test with each sub-score set to None individually; assert result in [0, 100] |
| urllib.robotparser RFC mismatch | Module 2: Robots | Test with robots.txt containing Allow override of broad Disallow; verify correct result |
| BeautifulSoup encoding / chardet | Module 1: Crawler | Test with Latin-1 and GB2312 encoded pages; verify no mojibake in extracted text |
| Streamlit pipeline rerun | Module 8: Streamlit | Click all UI elements post-analysis; verify no duplicate HTTP requests in logs |

---

## Sources

- [extruct Issue #45: Accept JSON parsing errors in JSON-LD extractor](https://github.com/scrapinghub/extruct/issues/45)
- [extruct Issue #87: Handle badly formatted JSON-LD data](https://github.com/scrapinghub/extruct/issues/87)
- [extruct Issue #109: Parsing of JSON-LD breaks when followed by a semicolon](https://github.com/scrapinghub/extruct/issues/109)
- [extruct Issue #112: html parsing fail on empty documents](https://github.com/scrapinghub/extruct/issues/112)
- [spaCy Issue #2508: Property for max doc length](https://github.com/explosion/spaCy/issues/2508)
- [spaCy Issue #2817: ValueError E088](https://github.com/explosion/spaCy/issues/2817)
- [CPython Issue #116740: urllib.robotparser misbehaves with Disallow/Allow order](https://github.com/python/cpython/issues/116740)
- [DEV.to: Python's urllib.robotparser Is Subtly Wrong](https://dev.to/sendotltd/pythons-urllibrobotparser-is-subtly-wrong-and-why-that-matters-for-seo-41kn)
- [Streamlit Issue #10192: Infinite spinner loop with st.stop in cached functions](https://github.com/streamlit/streamlit/issues/10192)
- [Streamlit Issue #6687: Non-blocking background execution](https://github.com/streamlit/streamlit/issues/6687)
- [Streamlit Docs: st.cache_data](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
- [datawookie: Accelerating BeautifulSoup Encoding Detection](https://datawookie.dev/blog/2025/10/accelerating-beautifulsoup-encoding-detection/)
- [Scrapfly: How to fix SSLError in Python requests](https://scrapfly.io/blog/answers/python-requests-exception-sllerror)
- [ScrapeOps: Web Scraping Part 5 - Using Fake User-Agents and Browser Headers](https://scrapeops.io/web-scraping-playbook/beginners-web-scraping-guide-part-5/)
- [Crawlee Blog: Common problems in web scraping](https://crawlee.dev/blog/common-problems-in-web-scraping)
- [textstat PyPI](https://pypi.org/project/textstat/)

---
*Pitfalls research for: Python web scraping + NLP scoring tool (AI Readiness Checker)*
*Researched: 2026-05-02*
