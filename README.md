# AI Readiness Checker

**One command to see if AI search engines can find your website.**

```bash
pip install ai-readiness-checker
checker https://yoursite.com
```

When someone searches with ChatGPT, Perplexity, Claude, or Google AI Overviews — will your website show up? This tool scores your site across four signals AI search engines care about, gives you an A-F grade, and tells you exactly what to fix.

---

## Two Ways to Use It

### Use Case 1: Command-Line Tool (for developers)

You have a website. You want to know if AI can find it. One command:

```bash
$ checker https://my-cool-saas.com --fix
```

**What you see:**
```
─────────────────────────── AI Readiness Score Card ────────────────────────────
URL: https://my-cool-saas.com

  B   Overall Score: 72.4/100

                        Module Breakdown
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Module     ┃ Score ┃ Weight ┃ Weighted ┃ Bar                  ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Robots.txt │  0.80 │    20% │     16.0 │ ████████████████░░░░ │
│ llms.txt   │  0.00 │    15% │      0.0 │ ░░░░░░░░░░░░░░░░░░░░ │
│ Schema     │  0.70 │    30% │     21.0 │ ██████████████░░░░░░ │
│ Content    │  0.55 │    35% │     19.3 │ ███████████░░░░░░░░░ │
└────────────┴───────┴────────┴──────────┴──────────────────────┘

Recommendations:
  [HIGH]   No llms.txt found. Create one to help AI models understand your page.
  [MEDIUM] Your Q&A density is low. Add FAQ sections — AI loves Q&A format.

────────────────────────────────────────────────────────────
AI Improvement Summary
────────────────────────────────────────────────────────────
Skills invoked: fix-schema, fix-readability, fix-qa, fix-llms-txt
Changes made: 4
  • Added FAQPage JSON-LD block (LLM-generated)
  • Rewrote 3 paragraph(s) for better readability
  • Added AI-generated Q&A section with 4 questions
  • Generated AI-powered llms.txt (847 chars) for https://my-cool-saas.com
```

**Every command:**

| Command | What it does |
|---------|-------------|
| `checker <url>` | Score a site |
| `checker <url> --fix` | Score + apply fixes (template-based, free) |
| `checker <url> --fix --llm-backend openai` | Score + AI-powered fixes |
| `checker <url> --fix --llm-backend ollama` | Score + local AI fixes (free) |
| `checker <url> -o report.json` | Export results to JSON |
| `checker --batch urls.csv -o results.csv` | Score multiple URLs |
| `checker --serve --port 8000` | Start REST API |
| `checker --mcp` | Start MCP server for Claude Code/Cursor |
| `streamlit run app.py` | Interactive dashboard |

### Use Case 2: Vibe Coding (Claude Code Skill)

You're building a website with Claude Code. You just deployed. Now you wonder: "will AI search engines actually see this?"

```
You: "Check my site's AI readiness"
Claude: [runs checker, shows grade, routes findings to fix skills]
        "Your site scored 55/C. Here's what's holding you back:
         
         1. No llms.txt → I can fix this right now with built-in fix-llms-txt
         2. Low readability → The `taste` skill would nail this. 
            Install it with: /plugin install taste@claude-plugins-official
         
         Want me to apply the fixes I can handle?"
```

The skill **cross-references every finding** with complementary skills. If your readability is poor but our built-in fixer can't fully solve it, it routes you to `taste` or `uiux-promax`. It checks whether you have those skills installed and gives you the exact install command if not.

**To install the skill:** copy `.claude/skills/ai-readiness-checker/skill.md` into your project's `.claude/skills/` directory. Claude Code auto-discovers it.

---

## What It Checks

| Signal | What It Means | Weight | Example |
|--------|--------------|--------|---------|
| **robots.txt** | Are AI crawlers allowed? Checks 7 bots (GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot-Extended, Amazonbot) | 20% | Blocking GPTBot loses 0.07 from your score |
| **llms.txt** | Do you have a machine-readable summary for LLMs? | 15% | A missing llms.txt adds a HIGH priority recommendation |
| **Schema** | Do you have structured data (JSON-LD, microdata, RDFa)? Tracks 6 types: Product, FAQPage, Organization, BreadcrumbList, Article, Review | 30% | FAQPage + Product are weighted highest (0.25 each) |
| **Content** | Is your text readable, well-structured, with good heading hierarchy and Q&A density? | 35% | Uses Flesch Reading Ease, Gunning Fog, NER, heading analysis |

---

## Fix Skills (Built-in)

When you run `--fix`, these skills auto-apply. With an LLM backend, they're AI-powered; without, they use fast templates.

| Skill | What it fixes | With LLM backend |
|-------|--------------|-----------------|
| `fix-schema` | Missing JSON-LD structured data | Generates context-aware blocks from your content |
| `fix-headings` | Duplicate H1s, broken hierarchy | Rewrites heading structure for clarity |
| `fix-readability` | Dense, hard-to-read paragraphs | Rewrites text at 7th-9th grade reading level |
| `fix-qa` | Low Q&A density | Generates real FAQ from your page content |
| `fix-llms-txt` | Missing llms.txt | Generates proper llms.txt from headings + links |

---

## Score Ranges

| Score | Grade | What It Means |
|-------|-------|---------------|
| 85-100 | **A** | Excellent — AI crawlers fully see and understand your site |
| 70-84 | **B** | Good — mostly visible, a few minor fixes |
| 55-69 | **C** | Okay — significant gaps AI crawlers will miss |
| 40-54 | **D** | Poor — AI is missing key information |
| 0-39 | **F** | Critical — AI cannot effectively access your site |

---

## Architecture

```
URL → Crawler → [robots.txt, llms.txt, schema, content] → Scorer → Report
                                                                    ↓
                                                              [optional]
                                                              LLM Agent
                                                              (--fix flag)
                                                              ↓
                                                      Improved HTML + Diff + Explanation
```

---

## Install

```bash
pip install ai-readiness-checker
python -m spacy download en_core_web_sm
```

Or from source:

```bash
git clone https://github.com/yourusername/ai-readiness-checker.git
cd ai-readiness-checker
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
pytest  # 208 tests
```

**Requirements:** Python 3.10+, spaCy `en_core_web_sm`.  
**Optional:** OpenAI/Anthropic API key or local Ollama for AI-powered fixes.

---

## Project Structure

```
ai-readiness-checker/
├── src/checker/          # Python package (pip install)
│   ├── __main__.py       # CLI entry point
│   ├── orchestrator.py   # Pipeline: crawl → analyze → score
│   ├── scorer.py         # Weighted scoring + recommendations
│   ├── agent.py          # V2 LLM agent: decides skills, merges results
│   ├── skills/           # 7 fix skills (schema, headings, readability, qa, llms, preview, explain)
│   ├── llm_backends.py   # Ollama, OpenAI, Anthropic backends
│   ├── api_server.py     # FastAPI server
│   ├── mcp_server.py     # MCP server for Claude Code / Cursor
│   ├── crawler.py        # URL fetcher with realistic headers
│   ├── robots_txt.py     # robots.txt parser (7 AI bots)
│   ├── llms_txt.py       # llms.txt validator
│   ├── schema_analyzer.py # Structured data extraction (extruct)
│   ├── content_analyzer.py # NLP content analysis (spaCy, textstat)
│   ├── cli_renderer.py   # Rich terminal formatting
│   └── contracts.py      # All data contracts
├── .claude/skills/       # Claude Code skill (vibe coding interface)
│   └── ai-readiness-checker/skill.md
├── tests/                # 208 tests (pytest)
├── app.py                # Streamlit dashboard
└── pyproject.toml        # Package config, deps, entry points
```

---

## License

MIT — use it, fork it, ship it, build on it. No strings attached.

The `.claude/skills/ai-readiness-checker/` skill file is also MIT licensed. If you copy it into your own project, attribution is appreciated but not required.
