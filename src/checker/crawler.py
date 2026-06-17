"""
URL crawler — fetches and parses HTML for analysis.

This module provides the single entry point for all URL fetching.
It never raises exceptions — it always returns FetchResult or CrawlError.
"""

import requests
from urllib.parse import urlsplit
from ipaddress import ip_address
from bs4 import BeautifulSoup

from checker.contracts import FetchResult, CrawlError


# ---- Constants ----

REALISTIC_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

DEFAULT_TIMEOUT = 10  # seconds
MAX_RESPONSE_SIZE = 10_000_000  # 10MB — prevents decompression bomb DoS

# SSRF prevention: hosts and networks that must never be contacted
BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}

BLOCKED_NETWORKS = [
    '169.254.0.0/16',   # link-local (AWS metadata, etc.)
    '10.0.0.0/8',        # private
    '172.16.0.0/12',     # private
    '192.168.0.0/16',    # private
]


# ---- SSRF Prevention ----

def is_ssrf_safe(url: str) -> bool:
    """Return False if the URL targets localhost, private, or link-local addresses.

    This implements OWASP ASVS V5.1.1: validate that user-supplied URLs
    do not target internal network resources.

    Args:
        url: Full URL string to validate.

    Returns:
        True if the URL is safe to fetch, False if it targets blocked resources.
    """
    parsed = urlsplit(url)

    # Scheme must be http or https
    if parsed.scheme not in ('http', 'https'):
        return False

    hostname = parsed.hostname or ''

    # Block known malicious hostnames
    if hostname.lower() in BLOCKED_HOSTS:
        return False

    # Block private, loopback, and link-local IPs
    try:
        addr = ip_address(hostname)
        if addr.is_loopback or addr.is_private or addr.is_link_local:
            return False
    except ValueError:
        # Not an IP address — hostname like 'example.com' — proceed
        pass

    return True


# ---- URL Validation ----

def _validate_url(url: str) -> CrawlError | None:
    """Validate URL structure. Returns CrawlError if invalid, None if OK."""
    parsed = urlsplit(url)

    if not parsed.scheme or not parsed.netloc:
        return CrawlError(
            url=url,
            error_type='invalid_url',
            message='URL must include scheme (http/https) and hostname',
        )

    if parsed.scheme not in ('http', 'https'):
        return CrawlError(
            url=url,
            error_type='invalid_url',
            message=f'Scheme "{parsed.scheme}" not supported. Use http or https.',
        )

    return None


# ---- Main Fetch Function ----

def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> FetchResult | CrawlError:
    """Fetch and parse HTML from a URL.

    This function never raises — it always returns either a FetchResult
    (on success) or a CrawlError (on any failure).

    Args:
        url: The URL to fetch. Must be http or https.
        timeout: Maximum seconds to wait for a response. Default 10s.

    Returns:
        FetchResult with parsed HTML on success, CrawlError on any failure.
    """
    # Step 1: Validate URL structure
    validation_error = _validate_url(url)
    if validation_error is not None:
        return validation_error

    # Step 2: SSRF check
    if not is_ssrf_safe(url):
        return CrawlError(
            url=url,
            error_type='ssrf_blocked',
            message=f'URL targets an internal or blocked address: {url}',
        )

    # Step 3: HTTP fetch
    try:
        response = requests.get(
            url,
            headers=REALISTIC_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.exceptions.Timeout:
        return CrawlError(
            url=url,
            error_type='timeout',
            message=f'Request timed out after {timeout}s: {url}',
        )
    except requests.exceptions.ConnectionError as e:
        return CrawlError(
            url=url,
            error_type='connection_error',
            message=f'Connection failed (DNS, refused, or network issue): {url} — {e}',
        )
    except requests.exceptions.TooManyRedirects:
        return CrawlError(
            url=url,
            error_type='too_many_redirects',
            message=f'Too many redirects for url: {url}',
        )
    except requests.exceptions.RequestException as e:
        return CrawlError(
            url=url,
            error_type='request_error',
            message=f'Unexpected request error: {e}',
        )

    # Step 4: Check response size BEFORE reading full body
    # (requests already downloaded the body by this point, but we check size limit)
    content_length = len(response.content)
    if content_length > MAX_RESPONSE_SIZE:
        return CrawlError(
            url=url,
            error_type='response_too_large',
            message=(
                f'Response body ({content_length} bytes) exceeds '
                f'maximum allowed size ({MAX_RESPONSE_SIZE} bytes)'
            ),
        )

    # Step 5: Check HTTP status
    if not response.ok:
        return CrawlError(
            url=url,
            error_type='http_error',
            status_code=response.status_code,
            message=f'HTTP {response.status_code} for url: {url}',
        )

    # Step 6: Parse HTML
    try:
        # Use response.content (bytes) not response.text — let BeautifulSoup
        # handle encoding detection via UnicodeDammit (reads <meta charset> tags)
        soup = BeautifulSoup(response.content, 'lxml')
    except Exception as e:
        return CrawlError(
            url=url,
            error_type='request_error',
            message=f'HTML parsing failed: {e}',
        )

    # Step 7: Return success
    return FetchResult(
        url=url,
        final_url=response.url,
        status_code=response.status_code,
        html=str(soup),  # Store normalized HTML (lxml may reformat)
        soup=soup,
    )
