"""
Data contracts for the AI Readiness Checker.

This module is the single source of truth for all inter-module communication shapes.
Every downstream module imports its input/output contracts from here.

Phase 1: FetchResult, CrawlError
Phase 2: (future) RobotsAnalysis, LLMSTxtAnalysis
Phase 3: (future) SchemaAnalysis
Phase 4: (future) ContentAnalysis
Phase 5: (future) ScoreReport
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup


@dataclass
class CrawlError:
    """Structured error result when a crawl fails.

    Downstream modules receive this instead of catching exceptions.
    """

    url: str
    error_type: str
    # Valid error_type values:
    #   'invalid_url'        — URL malformed or non-http(s) scheme
    #   'ssrf_blocked'        — URL targets localhost/private/internal network
    #   'connection_error'    — DNS failure, connection refused, network unreachable
    #   'timeout'             — Request exceeded timeout (default 10s)
    #   'http_error'          — Server returned 4xx or 5xx status
    #   'too_many_redirects'  — Redirect chain exceeded requests' limit (30)
    #   'request_error'       — Catch-all for other requests exceptions
    #   'response_too_large'  — Response body exceeded MAX_RESPONSE_SIZE
    status_code: Optional[int] = None
    message: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class FetchResult:
    """Successful crawl result with parsed HTML.

    This is the root input contract for all four analysis modules
    (robots.txt, llms.txt, schema, content).
    """

    url: str  # Original requested URL
    final_url: str  # URL after all redirects resolved
    status_code: int  # HTTP status code (should be 2xx)
    html: str  # Raw HTML text (for serialization, report generation)
    soup: BeautifulSoup  # Pre-parsed BS4 tree (lxml parser) — cached to avoid re-parsing
    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

# TODO: v2 — CRAWL-03: add response.headers dict to FetchResult
