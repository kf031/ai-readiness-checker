"""
llms.txt analysis module — fetch, validate format, and score.

Checks /llms.txt at the target site's root path. Uses markdown-it-py
for token-level format validation per the llmstxt.org specification.
Consumed by Phase 5 scorer for the llms.txt component (15% weight).
"""

from datetime import datetime, timezone
from typing import Optional

import httpx
from markdown_it import MarkdownIt

from checker.contracts import LlmsResult


# ---- Constants ----

MAX_LLMS_SIZE = 1_048_576  # 1MB

LLMS_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/plain,text/markdown,text/html,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

DEFAULT_TIMEOUT = 10.0


# ---- Format Validation ----

def validate_llms_txt(text: str) -> tuple[bool, list[str]]:
    """Validate llms.txt format against the llmstxt.org specification.

    Uses markdown-it-py to parse the text into tokens, then checks:
    1. First heading token must be H1 (mandatory by spec)
    2. At least one H2 section must exist
    3. H2 sections must contain markdown links

    Args:
        text: Raw llms.txt content as a string.

    Returns:
        Tuple of (is_valid: bool, errors: list[str]). Empty errors list if valid.
    """
    errors = []
    md = MarkdownIt()
    tokens = md.parse(text)

    # Extract structural tokens
    heading_opens = []
    links = []

    # Recursively collect tokens of interest (link_open is nested inside
    # inline tokens in markdown-it-py v4.0.0)
    def _collect(tok_list):
        for t in tok_list:
            if t.type == 'heading_open':
                heading_opens.append(t)
            elif t.type == 'link_open':
                links.append(t)
            if hasattr(t, 'children') and t.children:
                _collect(t.children)

    _collect(tokens)

    # Rule 1: First heading must be H1 (mandatory)
    if not heading_opens:
        errors.append("Missing H1 heading (required by llms.txt spec)")
    elif heading_opens[0].tag != 'h1':
        errors.append(
            f"First heading is <{heading_opens[0].tag}>, expected <h1>"
        )

    # Rule 2: Must have at least one H2 section
    h2_headings = [h for h in heading_opens if h.tag == 'h2']
    if not h2_headings:
        errors.append("No H2 file-list sections found")

    # Rule 3: H2 sections must contain at least one markdown link
    if h2_headings and not links:
        errors.append("H2 sections present but no markdown links found")

    return len(errors) == 0, errors


# ---- Scoring ----

def compute_llms_score(found: bool, valid: Optional[bool]) -> float:
    """Compute llms.txt score based on presence and validity.

    Per D-03:
    - Valid (found + format correct): 1.0
    - Malformed (found + format invalid): 0.3
    - Missing (not found): 0.0

    Args:
        found: Whether llms.txt returned 200 OK.
        valid: Format validity (None if not found).

    Returns:
        Float: 1.0, 0.3, or 0.0.
    """
    if not found:
        return 0.0
    if valid is True:
        return 1.0
    return 0.3  # found but malformed


# ---- Fetch ----

def fetch_llms_txt(url: str, timeout: float = DEFAULT_TIMEOUT) -> LlmsResult:
    """Fetch and validate llms.txt from a website's root.

    This function NEVER raises — it always returns a LlmsResult.

    Args:
        url: The base URL of the site (e.g., "https://example.com").
        timeout: HTTP request timeout in seconds. Default 10.0.

    Returns:
        LlmsResult with found/valid/score fields populated.
    """
    llms_url = url.rstrip('/') + '/llms.txt'
    now = datetime.now(timezone.utc)

    try:
        with httpx.Client(
            timeout=timeout,
            headers=LLMS_HEADERS,
            follow_redirects=True,
        ) as client:
            response = client.get(llms_url)

        status_code = response.status_code

        # 404 = not found
        if status_code == 404:
            return LlmsResult(
                url=url,
                found=False,
                status_code=status_code,
                fetch_error=None,
                valid=None,
                validation_errors=[],
                content_preview=None,
                raw_text=None,
                fetched_at=now,
            )

        # 4xx/5xx = infrastructure error
        if status_code >= 400:
            return LlmsResult(
                url=url,
                found=False,
                status_code=status_code,
                fetch_error=f"http_error_{status_code}",
                valid=None,
                validation_errors=[],
                content_preview=None,
                raw_text=None,
                fetched_at=now,
            )

        # Success: check size limit
        content = response.text
        if len(content.encode('utf-8')) > MAX_LLMS_SIZE:
            return LlmsResult(
                url=url,
                found=False,
                status_code=status_code,
                fetch_error="response_too_large",
                valid=None,
                validation_errors=[],
                content_preview=None,
                raw_text=None,
                fetched_at=now,
            )

        # Validate format
        is_valid, validation_errors = validate_llms_txt(content)

        # Extract 500-char content preview
        content_preview = content[:500]

        return LlmsResult(
            url=url,
            found=True,
            status_code=status_code,
            fetch_error=None,
            valid=is_valid,
            validation_errors=validation_errors,
            content_preview=content_preview,
            raw_text=content,
            fetched_at=now,
        )

    except httpx.TimeoutException:
        return LlmsResult(
            url=url,
            found=False,
            fetch_error="timeout",
            valid=None,
            validation_errors=[],
            content_preview=None,
            raw_text=None,
            fetched_at=now,
        )
    except httpx.ConnectError:
        return LlmsResult(
            url=url,
            found=False,
            fetch_error="connection_error",
            valid=None,
            validation_errors=[],
            content_preview=None,
            raw_text=None,
            fetched_at=now,
        )
    except httpx.HTTPStatusError as e:
        return LlmsResult(
            url=url,
            found=False,
            status_code=e.response.status_code,
            fetch_error=f"http_error_{e.response.status_code}",
            valid=None,
            validation_errors=[],
            content_preview=None,
            raw_text=None,
            fetched_at=now,
        )
    except Exception:
        return LlmsResult(
            url=url,
            found=False,
            fetch_error="request_error",
            valid=None,
            validation_errors=[],
            content_preview=None,
            raw_text=None,
            fetched_at=now,
        )
