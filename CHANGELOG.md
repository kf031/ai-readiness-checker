# Changelog

## 0.1.0 (2026-06-17)

Initial release.

### What's included

- **Pipeline:** crawl → robots.txt → llms.txt → schema → content → scorer → report
- **CLI:** `checker <url>` with Rich-formatted score card, colored grades, Unicode bars
- **Streamlit dashboard:** interactive UI with per-module expanders and recommendations
- **AI fixes:** 5 built-in fix skills (schema, headings, readability, QA, llms.txt)
- **LLM backends:** Ollama (local), OpenAI (GPT-4), Anthropic (Claude)
- **Batch mode:** `checker --batch urls.csv`
- **JSON export:** `checker <url> -o report.json`
- **FastAPI server:** `checker --serve`
- **MCP server:** `checker --mcp` for Claude Code / Cursor / Windsurf
- **Claude Code skill:** `.claude/skills/ai-readiness-checker/` for vibe coding
- **Meta-skill routing:** cross-references findings with complementary skills (taste, uiux-promax, etc.)
- **208 tests** (pytest), all passing
- **Python 3.10+**, MIT licensed

### Known limitations

- spaCy `en_core_web_sm` is a heavy dependency (~15MB). Entity and QA scores return 0.0 if not installed.
- Template-based fixes (no LLM) are basic regex — LLM backends produce much better results.
- Content analysis is English-only (spaCy English model).
- No non-English language support yet.
