"""Tests for crawler.py — covers CRAWL-01 and CRAWL-02."""

import pytest
from unittest.mock import patch, Mock
import requests

# Import the module under test
from src.checker.crawler import fetch_url, MAX_RESPONSE_SIZE, BLOCKED_HOSTS, BLOCKED_NETWORKS, is_ssrf_safe
from src.checker.contracts import FetchResult, CrawlError


# ----- CRAWL-01: Successful fetch -----

def test_fetch_url_success(mock_success_response):
    """CRAWL-01: Valid URL returns FetchResult with parsed HTML and realistic headers."""
    with patch('requests.get', return_value=mock_success_response) as mock_get:
        result = fetch_url('https://example.com')

    assert isinstance(result, FetchResult)
    assert result.url == 'https://example.com'
    assert result.status_code == 200
    assert len(result.html) > 0
    assert result.soup is not None
    assert result.final_url == 'https://example.com'

    # Verify realistic headers were passed
    call_kwargs = mock_get.call_args.kwargs
    assert 'headers' in call_kwargs
    assert 'User-Agent' in call_kwargs['headers']
    assert 'Chrome' in call_kwargs['headers']['User-Agent']
    # Verify timeout was set
    assert call_kwargs['timeout'] == 10


def test_follows_redirects(mock_redirect_response):
    """CRAWL-01: Redirect chain is followed and final_url reflects destination."""
    with patch('requests.get', return_value=mock_redirect_response):
        result = fetch_url('https://example.com/start')

    assert isinstance(result, FetchResult)
    assert result.url == 'https://example.com/start'         # original
    assert 'final-destination' in result.final_url           # after redirect
    assert result.final_url != result.url


def test_html_parsed_with_lxml(mock_success_response):
    """CRAWL-01: HTML is parsed with lxml parser (not html.parser)."""
    with patch('requests.get', return_value=mock_success_response):
        result = fetch_url('https://example.com')

    # BeautifulSoup with lxml should produce a valid tree
    assert result.soup.find('h1') is not None
    assert result.soup.find('h1').get_text() == 'Welcome to the Test Page'
    assert result.soup.find('title') is not None


# ----- CRAWL-02: Graceful error handling -----

def test_invalid_url_no_scheme():
    """CRAWL-02: URL without scheme returns CrawlError(error_type='invalid_url')."""
    result = fetch_url('example.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'invalid_url'
    assert result.url == 'example.com'
    assert 'scheme' in result.message.lower()


def test_invalid_url_unsupported_scheme():
    """CRAWL-02: Non-http(s) scheme returns CrawlError(error_type='invalid_url')."""
    result = fetch_url('ftp://files.example.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'invalid_url'


def test_ssrf_file_url_blocked():
    """CRAWL-02: file:// URL returns CrawlError(error_type='ssrf_blocked' or 'invalid_url')."""
    result = fetch_url('file:///etc/passwd')

    assert isinstance(result, CrawlError)
    assert result.error_type in ('ssrf_blocked', 'invalid_url')


def test_ssrf_localhost_blocked():
    """CRAWL-02: localhost/127.0.0.1 URL returns CrawlError(error_type='ssrf_blocked')."""
    result = fetch_url('http://127.0.0.1:8080')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'ssrf_blocked'


def test_ssrf_private_ip_blocked():
    """CRAWL-02: Private IP (10.x, 172.16.x, 192.168.x) returns ssrf_blocked."""
    for url in ['http://10.0.0.1', 'http://172.16.0.1', 'http://192.168.0.1', 'http://169.254.0.1']:
        result = fetch_url(url)
        assert isinstance(result, CrawlError), f"Expected CrawlError for {url}"
        assert result.error_type == 'ssrf_blocked', f"Wrong error_type for {url}: {result.error_type}"


def test_connection_error_returns_crawlerror():
    """CRAWL-02: ConnectionError returns CrawlError, not exception."""
    with patch('requests.get', side_effect=requests.exceptions.ConnectionError('refused')):
        result = fetch_url('https://valid-looking-url.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'connection_error'
    assert 'refused' in result.message or 'Connection' in result.message


def test_timeout_returns_crawlerror():
    """CRAWL-02: Timeout returns CrawlError with error_type='timeout'."""
    with patch('requests.get', side_effect=requests.exceptions.Timeout('timed out')):
        result = fetch_url('https://slow-server.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'timeout'


def test_http_404_returns_crawlerror(mock_404_response):
    """CRAWL-02: HTTP 4xx returns CrawlError with error_type='http_error'."""
    with patch('requests.get', return_value=mock_404_response):
        result = fetch_url('https://example.com/missing')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'http_error'
    assert result.status_code == 404


def test_http_500_returns_crawlerror(mock_500_response):
    """CRAWL-02: HTTP 5xx returns CrawlError with error_type='http_error'."""
    with patch('requests.get', return_value=mock_500_response):
        result = fetch_url('https://example.com/broken')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'http_error'
    assert result.status_code == 500


def test_too_many_redirects_returns_crawlerror():
    """CRAWL-02: TooManyRedirects returns CrawlError."""
    with patch('requests.get', side_effect=requests.exceptions.TooManyRedirects('too many')):
        result = fetch_url('https://redirect-loop.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'too_many_redirects'


def test_response_too_large_returns_crawlerror():
    """CRAWL-02: Response exceeding MAX_RESPONSE_SIZE returns CrawlError."""
    import requests as rq
    resp = rq.Response()
    resp.status_code = 200
    resp.url = 'https://huge-page.com'
    resp._content = b'x' * (MAX_RESPONSE_SIZE + 1)

    with patch('requests.get', return_value=resp):
        result = fetch_url('https://huge-page.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'response_too_large'


def test_request_exception_returns_crawlerror():
    """CRAWL-02: Generic RequestException returns CrawlError with error_type='request_error'."""
    with patch('requests.get', side_effect=requests.exceptions.RequestException('unknown')):
        result = fetch_url('https://mystery-error.com')

    assert isinstance(result, CrawlError)
    assert result.error_type == 'request_error'


def test_crawlerror_has_timestamp():
    """CRAWL-02: All CrawlError results include a timestamp."""
    result = fetch_url('not-a-url')

    assert isinstance(result, CrawlError)
    assert result.timestamp is not None


# ----- Contract guarantees -----

def test_fetch_url_never_raises():
    """CRAWL-02: fetch_url() never raises — always returns FetchResult or CrawlError."""
    import random
    import string

    # Test with a truly garbage URL that might trigger edge cases
    garbage = ''.join(random.choices(string.printable, k=50))
    result = fetch_url(garbage)

    # Must return something, not raise
    assert result is not None
    assert isinstance(result, (FetchResult, CrawlError))


# ----- SSRF prevention unit tests -----

def test_is_ssrf_safe_valid_url():
    """SSRF: Normal public URLs pass SSRF check."""
    assert is_ssrf_safe('https://example.com') is True
    assert is_ssrf_safe('http://sub.domain.co.uk/path?q=1') is True


def test_is_ssrf_safe_file_url():
    """SSRF: file:// scheme fails SSRF check."""
    assert is_ssrf_safe('file:///etc/passwd') is False


def test_is_ssrf_safe_localhost():
    """SSRF: localhost/127.0.0.1/::1/0.0.0.0 fail SSRF check."""
    for host in ['http://localhost', 'http://127.0.0.1', 'http://[::1]', 'http://0.0.0.0']:
        assert is_ssrf_safe(host) is False, f"Expected {host} to fail SSRF check"


def test_is_ssrf_safe_private_ips():
    """SSRF: Private IP ranges fail SSRF check."""
    for ip in ['http://10.0.0.1', 'http://172.16.0.1', 'http://192.168.1.1', 'http://169.254.1.1']:
        assert is_ssrf_safe(ip) is False, f"Expected {ip} to fail SSRF check"
