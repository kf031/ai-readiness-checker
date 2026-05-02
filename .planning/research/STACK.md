# Stack Research

**Domain:** Python web scraping + NLP scoring tool (AI readiness checker)
**Researched:** 2026-05-02
**Confidence:** HIGH (all versions verified against PyPI, official docs)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | 3.11 is the minimum for pandas 3.x; 3.12 works with all libraries below; avoid 3.13+ until spaCy wheels ship reliably |
| requests | 2.33.1 | HTTP fetching | Synchronous, zero learning curve, sufficient for single-URL analysis; httpx offers no advantage here (async not needed) |
| beautifulsoup4 | 4.14.3 | HTML parsing | Standard, battle-tested; pair with lxml backend for 5-10x speed vs html.parser |
| lxml | >=5.0 | HTML parser backend for BS4 | Official BS4 recommendation for speed; required as a separate install |
| extruct | 0.18.0 | Structured data extraction (JSON-LD, microdata, RDFa) | Only library that handles all three formats in a single call; no production-ready alternative |
| spaCy | 3.8.14 | NLP pipeline: entity detection, POS tagging | Fastest production NLP library for entity recognition; en_core_web_sm requires a separate download step (see gotchas) |
| textstat | 0.7.13 | Readability scoring (Flesch, Gunning Fog, etc.) | Zero-dependency, correct choice; actively maintained as of Feb 2026 |
| streamlit | 1.57.0 | Demo web UI | Best Python-native way to ship an interactive demo with no backend; now requires Python >=3.10 |
| pandas | 3.0.2 | Score table assembly, report DataFrames | Major version released Jan 2026; requires Python >=3.11 — this sets the project's minimum Python floor |
| rich | 15.0.0 | CLI formatted output | Standard for Python CLIs; tables, progress bars, color — no alternative competes |
| pytest | 9.0.3 | Testing | Standard; supports Python 3.10-3.14 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lxml | >=5.0 | BS4 parser backend + extruct dependency | Install alongside BS4; extruct also pulls it in, so it will be present either way |
| urllib.robotparser | stdlib | robots.txt parsing | Built into Python — no third-party library needed for this project's use case (checking specific bot names) |
| pytest-mock | >=3.14 | Mock HTTP responses in tests | Use for any test that would otherwise make live HTTP calls |
| pytest-cov | >=6.0 | Test coverage reporting | Optional but recommended for a portfolio-quality project |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pip-tools (pip-compile) | Lock dependency versions | Generates requirements.txt from requirements.in; prevents "works on my machine" issues |
| python-dotenv | Environment config (if needed) | Not needed for v1, but include if you add any API keys later |
| pre-commit + ruff | Linting and formatting | Optional for v1; worthwhile if this becomes a portfolio piece with contributors |

## Installation

```bash
# Core runtime
pip install requests==2.33.1 beautifulsoup4==4.14.3 lxml extruct==0.18.0
pip install spacy==3.8.14 textstat==0.7.13
pip install streamlit==1.57.0 pandas==3.0.2 rich==15.0.0

# spaCy model — REQUIRED SEPARATE STEP, cannot be in requirements.txt as a package name
python -m spacy download en_core_web_sm

# Testing
pip install pytest==9.0.3 pytest-mock pytest-cov

# requirements.txt pin for spaCy model (use direct URL format)
# en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| requests | httpx | httpx's advantages (async, HTTP/2) don't apply to a single-URL synchronous tool; adds complexity for zero benefit here |
| requests | playwright / selenium | Browser automation is overkill; this tool targets content and metadata, not JS-rendered pages |
| beautifulsoup4 + lxml | lxml directly | BS4 offers a much friendlier API; the raw lxml API is verbose and error-prone for newcomers |
| beautifulsoup4 + lxml | selectolax | Marginally faster but far less documentation; not worth the unfamiliarity for this use case |
| spaCy en_core_web_sm | NLTK | spaCy has better entity detection and is faster; NLTK requires more manual pipeline assembly |
| spaCy en_core_web_sm | en_core_web_md / lg | Larger models add accuracy for multi-document NLP; for single-page entity detection, sm is sufficient and avoids a 40-560MB download |
| spaCy en_core_web_sm | transformers (HuggingFace) | GPU/large RAM required; incompatible with the "no GPU, fast, open-source" constraint |
| textstat | py-readability-metrics | textstat is simpler and actively maintained; py-readability-metrics has older commit history |
| urllib.robotparser | reppy | reppy is unmaintained (archived on GitHub); reppy2 exists but adds a dependency for functionality stdlib handles adequately |
| pandas | polars | polars 3.x is faster but requires more relearning; pandas is better documented for newcomers and the data volumes here are trivial (one URL at a time) |
| rich | click | rich handles formatted output; click handles CLI argument parsing — these are complementary, not competing (use both if needed) |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| scrapy | Full crawl framework; massive overhead for a single-URL tool | requests + bs4 |
| reppy (PyPI) | Project is archived/unmaintained on GitHub | urllib.robotparser (stdlib) |
| newspaper3k / newspaper4k | Article extraction library that fights with direct HTML parsing; opinionated about content boundaries | bs4 + custom extraction |
| pandas < 3.0 | Copy-on-Write is the new default; mixing old idioms causes FutureWarning floods and silent chained-assignment bugs | pandas 3.0.2 |
| Python 3.10 | pandas 3.x requires Python >=3.11 — you would hit an install error immediately | Python 3.11+ |
| Python 3.13+ | spaCy 3.8.x wheels are not yet built for 3.13 on all platforms (as of research date); may require compiling from source | Python 3.11 or 3.12 |

## Stack Patterns by Variant

**If adding batch URL / CSV upload (v2):**
- Switch HTTP fetching to httpx with async for concurrent requests
- Add asyncio task management or use tenacity for retries
- Keep everything else the same

**If adding a hosted API (v2):**
- Wrap the scorer in a FastAPI app (not Flask — FastAPI has async-native support and auto-generates OpenAPI docs)
- Keep Streamlit as a separate frontend that calls the API

**If content analysis needs to handle JS-heavy sites (v2):**
- Add playwright as an optional fetching backend
- Do not add it to v1 — it's a 150MB browser download that breaks the "lightweight open-source tool" positioning

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| extruct 0.18.0 | Python 3.8–3.12, w3lib >=2.0 | RDFa extraction is marked experimental; safe to call with `syntaxes=['json-ld', 'microdata']` to skip it |
| spaCy 3.8.14 | Python 3.9–3.14 | Model version must match spaCy version: en_core_web_sm-3.8.x required for spaCy 3.8.x |
| pandas 3.0.2 | Python >=3.11 | This is the hard floor for the whole project — if you use pandas, you need 3.11+ |
| streamlit 1.57.0 | Python >=3.10 | No conflict with pandas' 3.11 requirement |
| requests 2.33.1 | Python >=3.10 | Requires Python 3.10+ as of 2.32.x series |

## Gotchas

### spaCy model is not a normal pip package
`pip install spacy` does NOT install the language model. You must run `python -m spacy download en_core_web_sm` as a separate step after pip install. In automated environments (CI, Docker), add this as an explicit RUN step. For requirements.txt, use the direct GitHub wheel URL format shown in the Installation section above.

### extruct's RDFa parser is unstable
Calling `extruct.extract(html, syntaxes=['json-ld', 'microdata', 'rdfa'])` can raise parsing errors on malformed markup. Safe default: restrict to `syntaxes=['json-ld', 'microdata']` — these cover the vast majority of schema.org usage in practice and are more stable. Add `uniform=True` to normalize the output structure across syntaxes.

### pandas 3.0 Copy-on-Write breaks old patterns
`df['col'][0] = value` (chained assignment) silently fails in pandas 3.0. Use `df.loc[row, col] = value` everywhere. If you follow pandas 3.0 idioms from the start, this is not a problem — it only bites when copying old pandas 1.x/2.x code snippets.

### requests does not follow all redirects by default on POST
For this project, all requests are GET, so `allow_redirects=True` (the default) is fine. No action needed.

### lxml must be installed separately even though extruct depends on it
extruct lists lxml as a dependency, so `pip install extruct` will install lxml. However, to use lxml as the BS4 parser backend, you must explicitly pass `BeautifulSoup(html, 'lxml')`. If lxml is missing, BS4 silently falls back to html.parser without warning unless you specify the parser explicitly.

## Sources

- PyPI: extruct 0.18.0 — version, Python support, release date (Nov 2024)
- PyPI: spaCy 3.8.14 — version, Python support (requires 3.9–3.14)
- PyPI: textstat 0.7.13 — version confirmed (Feb 2026)
- PyPI: streamlit 1.57.0 — version, Python >=3.10 requirement (Apr 2026)
- PyPI: pandas 3.0.2 — version, Python >=3.11 requirement (Mar 2026)
- PyPI: requests 2.33.1 — version, Python >=3.10 (Mar 2026)
- PyPI: beautifulsoup4 4.14.3 — version (Nov 2025)
- PyPI: rich 15.0.0 — version (Apr 2026)
- PyPI: pytest 9.0.3 — version (Apr 2026)
- GitHub: scrapinghub/extruct issues — maintenance status (39 open issues, last activity Mar 2025)
- spaCy docs (spacy.io/usage) — model download requirement, version pinning
- pandas whatsnew v3.0.0 — Copy-on-Write default, Python 3.11 minimum floor
- ScrapingAnt / Scrapfly: httpx vs requests comparison — confirmed requests sufficient for sync single-URL use
- Python docs: urllib.robotparser — confirmed stdlib handles Crawl-delay and standard directives

---
*Stack research for: AI Readiness Checker — Python web scraping + NLP scoring tool*
*Researched: 2026-05-02*
