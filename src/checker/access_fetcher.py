"""
Concurrent fetch orchestrator for Phase 2 access signals.

Fetches robots.txt and llms.txt concurrently using httpx.AsyncClient
with asyncio.gather. Falls back to sequential synchronous fetches if
the event loop is unavailable or conflicts.

Per D-05: try httpx.AsyncClient first, fall back to sequential.
"""

import asyncio
from typing import Tuple

import httpx

from src.checker.robots_txt import fetch_robots_txt, RobotsResult
from src.checker.llms_txt import fetch_llms_txt, LlmsResult


# ---- Constants ----

ACCESS_HEADERS = {
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


# ---- Async Concurrent Fetch ----

async def _fetch_both_async(
    url: str, timeout: float = DEFAULT_TIMEOUT
) -> Tuple[RobotsResult, LlmsResult]:
    """Internal async coroutine: fetch both resources concurrently.

    Uses a single AsyncClient for connection pooling efficiency.
    return_exceptions=True ensures one failure doesn't cancel the other.

    Args:
        url: Base URL of the target site.
        timeout: Request timeout in seconds.

    Returns:
        Tuple of (RobotsResult, LlmsResult).
    """
    robots_url = url.rstrip('/') + '/robots.txt'
    llms_url = url.rstrip('/') + '/llms.txt'

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=ACCESS_HEADERS,
        follow_redirects=True,
    ) as client:
        robots_resp, llms_resp = await asyncio.gather(
            client.get(robots_url),
            client.get(llms_url),
            return_exceptions=True,
        )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Process robots response
    if isinstance(robots_resp, Exception):
        robots_result = RobotsResult(
            url=url,
            exists=False,
            fetch_error="request_error",
            bots=[],
            raw_text=None,
            fetched_at=now,
        )
    else:
        robots_result = _process_robots_response(url, robots_resp, now)

    # Process llms response
    if isinstance(llms_resp, Exception):
        llms_result = LlmsResult(
            url=url,
            found=False,
            fetch_error="request_error",
            valid=None,
            validation_errors=[],
            content_preview=None,
            raw_text=None,
            fetched_at=now,
        )
    else:
        llms_result = _process_llms_response(url, llms_resp, now)

    return robots_result, llms_result


def _process_robots_response(url: str, response, now) -> RobotsResult:
    """Process an httpx Response into a RobotsResult.

    Delegates analysis to robots_txt.analyze_robots() to avoid
    duplicate HTTP calls — only raw text flows through.
    """
    from src.checker.robots_txt import analyze_robots, MAX_ROBOTS_SIZE

    status_code = response.status_code

    if status_code == 404:
        return RobotsResult(url=url, exists=False, status_code=status_code,
                           fetch_error=None, bots=[], raw_text=None, fetched_at=now)
    if status_code in (401, 403):
        return RobotsResult(url=url, exists=False, status_code=status_code,
                           fetch_error=None, bots=[], raw_text=None, fetched_at=now)
    if status_code >= 400:
        return RobotsResult(url=url, exists=False, status_code=status_code,
                           fetch_error=f"http_error_{status_code}", bots=[],
                           raw_text=None, fetched_at=now)

    content = response.text
    if len(content.encode('utf-8')) > MAX_ROBOTS_SIZE:
        return RobotsResult(url=url, exists=False, status_code=status_code,
                           fetch_error="response_too_large", bots=[],
                           raw_text=None, fetched_at=now)

    bot_statuses = analyze_robots(content)
    return RobotsResult(url=url, exists=True, status_code=status_code,
                       fetch_error=None, bots=bot_statuses,
                       raw_text=content, fetched_at=now)


def _process_llms_response(url: str, response, now) -> LlmsResult:
    """Process an httpx Response into a LlmsResult.

    Delegates validation to llms_txt.validate_llms_txt() to avoid
    duplicate HTTP calls — only raw text flows through.
    """
    from src.checker.llms_txt import validate_llms_txt, MAX_LLMS_SIZE

    status_code = response.status_code

    if status_code == 404:
        return LlmsResult(url=url, found=False, status_code=status_code,
                         fetch_error=None, valid=None, validation_errors=[],
                         content_preview=None, raw_text=None, fetched_at=now)
    if status_code >= 400:
        return LlmsResult(url=url, found=False, status_code=status_code,
                         fetch_error=f"http_error_{status_code}", valid=None,
                         validation_errors=[], content_preview=None,
                         raw_text=None, fetched_at=now)

    content = response.text
    if len(content.encode('utf-8')) > MAX_LLMS_SIZE:
        return LlmsResult(url=url, found=False, status_code=status_code,
                         fetch_error="response_too_large", valid=None,
                         validation_errors=[], content_preview=None,
                         raw_text=None, fetched_at=now)

    is_valid, validation_errors = validate_llms_txt(content)
    content_preview = content[:500]

    return LlmsResult(url=url, found=True, status_code=status_code,
                     fetch_error=None, valid=is_valid,
                     validation_errors=validation_errors,
                     content_preview=content_preview,
                     raw_text=content, fetched_at=now)


# ---- Public API ----

def fetch_access_signals(
    url: str, timeout: float = DEFAULT_TIMEOUT
) -> Tuple[RobotsResult, LlmsResult]:
    """Fetch and analyze robots.txt and llms.txt for a given URL.

    Attempts concurrent fetch via asyncio/httpx.AsyncClient first.
    Falls back to sequential synchronous fetches if the event loop
    is unavailable or encounters an error.

    Per D-05: try async first, fall back to sequential. Never crash.

    Args:
        url: The base URL of the target site (e.g., "https://example.com").
        timeout: HTTP request timeout in seconds. Default 10.0.

    Returns:
        Tuple of (RobotsResult, LlmsResult). Both are always populated
        — never None, never raises.
    """
    try:
        return asyncio.run(_fetch_both_async(url, timeout))
    except Exception:
        # Fallback: sequential synchronous fetches
        robots_result = fetch_robots_txt(url, timeout)
        llms_result = fetch_llms_txt(url, timeout)
        return robots_result, llms_result
