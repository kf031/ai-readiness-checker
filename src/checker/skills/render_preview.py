"""render-preview — Produces a visual before/after comparison HTML page."""

SKILL_NAME = "render-preview"
SKILL_DESCRIPTION = "Takes original + improved HTML and produces a visual before/after comparison HTML page."


def execute(html: str, report: dict, improved_html: str = "") -> dict:
    if not improved_html:
        return {"changes": ["No improved HTML to compare"], "modified_html": html, "target": "full"}

    diff_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Before / After — AI Readiness Checker</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; color: #1a1a1a; }}
  .header {{ background: #1a1a2e; color: #fff; padding: 1.5rem; text-align: center; }}
  .header h1 {{ font-size: 1.25rem; }}
  .url {{ color: #888; font-size: 0.85rem; margin-top: 0.25rem; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: #ccc; }}
  .panel {{ background: #fff; padding: 1rem; }}
  .panel h2 {{ font-size: 1rem; margin-bottom: 0.75rem; color: #555; text-transform: uppercase; letter-spacing: 0.05em; }}
  .before h2 {{ color: #c0392b; }}
  .after h2 {{ color: #27ae60; }}
  iframe {{ width: 100%; height: 80vh; border: 1px solid #ddd; border-radius: 4px; }}
</style>
</head>
<body>
<div class="header">
  <h1>Before / After Comparison</h1>
  <p class="url">{report.get("url", "Unknown URL")}</p>
</div>
<div class="grid">
  <div class="panel before">
    <h2>Original</h2>
    <iframe srcdoc="{_escape_html(html)}" sandbox="allow-same-origin"></iframe>
  </div>
  <div class="panel after">
    <h2>Improved</h2>
    <iframe srcdoc="{_escape_html(improved_html)}" sandbox="allow-same-origin"></iframe>
  </div>
</div>
</body>
</html>"""

    return {
        "changes": ["Generated before/after visual comparison"],
        "modified_html": diff_page,
        "target": "full",
    }


def _escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
