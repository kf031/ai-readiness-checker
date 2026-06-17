# AI Readiness Checker

**One command to see if AI search engines can find your website.**

```bash
pip install ai-readiness-checker
python -m checker https://yoursite.com
```

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-208%20passing-brightgreen.svg)](.)

When someone searches with ChatGPT, Perplexity, Claude, or Google AI Overviews — will your website show up? The AI Readiness Checker scores your site across four signals that AI search engines care about, giving you a letter grade and a prioritized fix list.

## What It Checks

| Signal | What It Means | Weight |
|--------|--------------|--------|
| **robots.txt** | Are AI crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.) allowed? | 20% |
| **llms.txt** | Do you have a machine-readable content summary for LLMs? | 15% |
| **Schema** | Do you have structured data (JSON-LD) for products, FAQs, articles? | 30% |
| **Content** | Is your text readable, well-structured, with clear headings? | 35% |

You get a **0-100 score** with a letter grade (A-F) and **actionable, prioritized recommendations.**

## Quick Start

### Install

```bash
pip install ai-readiness-checker
python -m spacy download en_core_web_sm  # needed for content analysis
```

### Score Any Website

```bash
python -m checker https://example.com
```

Output:
```
╔══════════════════════════════════════╗
║     AI READINESS SCORE CARD         ║
╚══════════════════════════════════════╝

URL: https://example.com
Overall Score: 62/100  Grade: C

Module Breakdown:
  robots.txt    ████████░░  0.80
  llms.txt      ░░░░░░░░░░  0.00
  schema        ████░░░░░░  0.40
  content       ██████░░░░  0.55

Recommendations:
  [HIGH] Add llms.txt file to help AI systems understand your content
  [MEDIUM] Add FAQPage schema markup for better AI visibility
```

### AI-Powered Fixes

The tool can generate an improved version of your page with fixes applied:

```bash
# Template-based fixes (fast, no API key needed)
python -m checker https://yoursite.com --fix

# AI-powered fixes (smarter, requires API key)
python -m checker https://yoursite.com --fix --llm-backend openai
python -m checker https://yoursite.com --fix --llm-backend ollama    # local, free
python -m checker https://yoursite.com --fix --llm-backend anthropic
```

**Fix skills:**
- `fix-schema` — Generates missing JSON-LD structured data
- `fix-headings` — Fixes heading hierarchy and merges duplicate H1s
- `fix-readability` — Rewrites dense paragraphs for better readability
- `fix-qa` — Adds FAQ sections derived from your content
- `fix-llms-txt` — Generates a proper llms.txt file

### Batch Mode

```bash
python -m checker --batch urls.csv -o results.csv
```

### Export to JSON

```bash
python -m checker https://example.com -o report.json
```

### Streamlit Dashboard

```bash
streamlit run app.py
```

Interactive web UI with score visualization, per-module expandable sections, and an "Improve My Site" button.

### FastAPI Server

```bash
python -m checker --serve --port 8000
```

Endpoints: `GET /analyze?url=...`, `POST /analyze`, `POST /fix`

### MCP Server (for Claude Code, Cursor, Windsurf)

```bash
python -m checker --mcp
```

Exposes `checker_analyze` and `checker_fix` as native MCP tools.

### Claude Code Skill

This project includes a Claude Code skill. When you're vibe coding, just say:

> "Check my site's AI readiness"

And Claude will run the checker and explain the results.

## Score Ranges

| Score | Grade | What It Means |
|-------|-------|---------------|
| 85-100 | **A** | Excellent — AI crawlers fully see your site |
| 70-84 | **B** | Good — mostly visible, minor fixes |
| 55-69 | **C** | Okay — significant gaps for AI |
| 40-54 | **D** | Poor — AI missing key information |
| 0-39 | **F** | Critical — AI cannot effectively access your site |

## Common Fixes

| Recommendation | What To Do |
|----------------|-----------|
| GPTBot is blocked | Add `User-agent: GPTBot` with `Allow: /` to robots.txt |
| No llms.txt found | Create an llms.txt file summarizing key pages |
| Missing FAQPage schema | Add JSON-LD FAQ structured data |
| Multiple H1 tags | Use exactly one `<h1>` per page |
| Low Q&A density | Add FAQ sections — AI loves Q&A format |
| No schema at all | Add at least Product, Organization, or Article JSON-LD |

## Architecture

```
URL → Crawler → [robots.txt, llms.txt, schema, content] → Scorer → Report
                                                                    ↓
                                                              [optional]
                                                              LLM Agent
                                                              (--fix flag)
```

## Development

```bash
git clone https://github.com/yourusername/ai-readiness-checker.git
cd ai-readiness-checker
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
pytest  # 208 tests
```

## Requirements

- Python 3.10+
- spaCy `en_core_web_sm` model (auto-install: `python -m spacy download en_core_web_sm`)
- Optional: OpenAI API key, Anthropic API key, or local Ollama for AI-powered fixes

## License

MIT — use it, fork it, ship it.
