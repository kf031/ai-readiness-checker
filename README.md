# AI Readiness Checker

**One command to see if AI search engines can find your website.**

```bash
pip install ai-readiness-checker
checker https://yoursite.com
```

When someone asks ChatGPT, Perplexity, or Claude a question your site answers — does it show up? Or is your content invisible?

This tool checks four things AI search engines look for, gives you a 0-100 score with a letter grade, and tells you what to fix. You can even have it **fix the problems for you.**

---

## What you see

```bash
$ checker https://my-site.com
```

While it runs, you see real-time progress:

```
  ◉  Fetching page
  ○  Checking robots.txt & llms.txt
  ○  Analyzing structured data
  ○  Analyzing content quality
  ○  Generating score report
```

Then the score card appears:

```
╭──────────────────────────────────────────────────────────╮
│                                                          │
│                  AI Readiness Score Card                 │
│                    https://my-site.com                   │
│                                                          │
│                      C   62.4/100                        │
│                                                          │
│   Robots.txt   ████████████████░░░░  (0.80)  w: 20%     │
│   llms.txt     ░░░░░░░░░░░░░░░░░░░░  (0.00)  w: 15%     │
│   Schema       ████████░░░░░░░░░░░░  (0.40)  w: 30%     │
│   Content      ███████████░░░░░░░░░  (0.55)  w: 35%     │
│                                                          │
│   ▲ HIGH    No llms.txt found                            │
│   ■ MEDIUM  Missing FAQPage schema                      │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

## Fix it automatically

```bash
$ checker https://my-site.com --fix --llm-backend openai
```

```
────────────────────────────────────────────────────────────
AI Improvement Summary
────────────────────────────────────────────────────────────
Skills invoked: fix-schema, fix-qa, fix-llms-txt
Changes made: 3
  • Added FAQPage JSON-LD block (LLM-generated from your content)
  • Added AI-generated Q&A section with 4 questions about your product
  • Generated llms.txt — 847 chars covering your key pages

────────────────────────────────────────────────────────────
Beyond Built-in Fixes — Complementary Tools
────────────────────────────────────────────────────────────
  Low readability → taste skill (copy tone & clarity)

Tip: Claude Code users can invoke these as skills (e.g., /taste)
```

## What it checks

| Signal | Weight | What matters |
|--------|--------|-------------|
| **robots.txt** | 20% | Are GPTBot, ClaudeBot, PerplexityBot, and 4 other AI crawlers allowed? |
| **llms.txt** | 15% | Is there a machine-readable summary telling LLMs what's on your site? |
| **Schema** | 30% | Do you have JSON-LD structured data? (Product, FAQ, Article, etc.) |
| **Content** | 35% | Is your text readable? Clear headings? Q&A sections? |

## How people use it

### As a CLI tool

```bash
checker <url>                            # Score a site
checker <url> --fix                      # Score + auto-fix (templates, no API key)
checker <url> --fix --llm-backend ollama # Score + local AI fixes (free)
checker <url> --fix --llm-backend openai # Score + GPT-4 fixes (needs key)
checker <url> -o report.json             # Export to JSON
checker --batch urls.csv                 # Score multiple sites
checker --serve                          # Start REST API on port 8000
streamlit run app.py                     # Interactive web dashboard
```

### While vibe coding (Claude Code skill)

Drop `.claude/skills/ai-readiness-checker/skill.md` into your project and Claude auto-discovers it. Then:

```
You: "Check my site's AI readiness"
Claude: [scores your site, shows grade, routes each finding to the right fix skill]
        "Your site scored 55/C. fix-llms-txt and fix-schema can handle two
         of these. For readability, try installing taste."
```

## Score ranges

| Score | Grade | What it means |
|-------|-------|--------------|
| 85–100 | **A** | Excellent. AI crawlers fully see and understand your site. |
| 70–84 | **B** | Good. Mostly visible, minor gaps. |
| 55–69 | **C** | Okay. Several things AI crawlers will miss. |
| 40–54 | **D** | Poor. AI is missing most of your content. |
| 0–39 | **F** | Invisible. AI cannot effectively access your site. |

## Fix skills (built-in)

| Skill | What it does | With LLM backend |
|-------|-------------|-----------------|
| `fix-schema` | Adds missing JSON-LD blocks | Generates context-aware schema from your content |
| `fix-headings` | Merges duplicate H1s, fixes hierarchy | AI rewrites headings for clarity |
| `fix-readability` | Detects dense paragraphs | AI rewrites at 7th-9th grade reading level |
| `fix-qa` | Adds FAQ sections | AI generates real Q&A from your page text |
| `fix-llms-txt` | Creates llms.txt | AI writes proper summary from your headings |

## Install

```bash
# Basic install — scores sites, no entity detection
pip install ai-readiness-checker

# Full install — entity extraction + Q&A analysis
pip install ai-readiness-checker[nlp]
python -m spacy download en_core_web_sm
```

Works without spaCy — entity and QA scores just return 0.0 gracefully.

From source:

```bash
git clone https://github.com/kf031/ai-readiness-checker.git
cd ai-readiness-checker
pip install -e ".[dev]"
pytest  # 208 tests
```

**Requires:** Python 3.10+, spaCy `en_core_web_sm`.  
**Optional:** OpenAI key, Anthropic key, or local Ollama for AI-powered fixes.

## License

MIT — use it, fork it, ship it, build on it.
