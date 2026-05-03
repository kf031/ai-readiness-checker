"""Shared fixtures for AI Readiness Checker tests."""

import pytest


# -- Sample HTML fixtures --

VALID_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Test Page</title>
    <meta name="description" content="A test page for crawler tests">
</head>
<body>
    <h1>Welcome to the Test Page</h1>
    <p>This is a paragraph with some content for testing.</p>
    <a href="/page2">Link to page 2</a>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "WebPage", "name": "Test Page"}
    </script>
</body>
</html>"""

EMPTY_HTML = "<html><head></head><body></body></html>"

MALFORMED_HTML = "<html><head><title>Broken<p>Unclosed tags<body><div>"


# -- URL fixtures --

VALID_URL = "https://example.com"
REDIRECT_URL = "https://httpbin.org/redirect/3"
HTTP_404_URL = "https://httpbin.org/status/404"
HTTP_500_URL = "https://httpbin.org/status/500"
INVALID_URL_NO_SCHEME = "example.com"
SSRF_FILE_URL = "file:///etc/passwd"
SSRF_LOCALHOST_URL = "http://127.0.0.1:8080"
SSRF_PRIVATE_URL = "http://10.0.0.1"
NON_ROUTABLE_URL = "http://thishostdefinitelydoesnotexist.invalid"



# -- robots.txt text fixtures (Phase 2) --

ROBOTS_TXT_ALL_ALLOWED = """User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: CCBot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: Applebot-Extended
Allow: /
User-agent: Amazonbot
Allow: /
"""

ROBOTS_TXT_ALL_BLOCKED = """User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: PerplexityBot
Disallow: /
User-agent: CCBot
Disallow: /
User-agent: Google-Extended
Disallow: /
User-agent: Applebot-Extended
Disallow: /
User-agent: Amazonbot
Disallow: /
"""

ROBOTS_TXT_MIXED = """User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: *
Disallow: /
"""

ROBOTS_TXT_CATCHALL = """User-agent: *
Disallow: /admin
Allow: /
"""

ROBOTS_TXT_EMPTY = """"""

ROBOTS_TXT_CASE_VARIANT = """User-agent: gptbot
Allow: /
User-agent: CLAUDEBOT
Disallow: /
"""

# -- llms.txt text fixtures (Phase 2) --

LLMS_TXT_VALID = """# Example Site LLMs Documentation

> This site provides information for AI language models.

This is the body text.

## API Docs
- [API Reference](/api) — Complete API documentation
- [SDK Guide](/sdk) — SDK installation and usage

## Data Sets
- [Training Data](/data/v1) — Version 1 training corpus
- [Validation Set](/data/val) — Validation data
"""

LLMS_TXT_NO_H1 = """This file has no heading.

## File List
- [File 1](/file1)
"""

LLMS_TXT_H1_ONLY = """# Just a heading
No sections below.
"""

LLMS_TXT_H2_NO_LINKS = """# Site Documentation

## Empty Section
This section has no links at all.

## Another Section
Still no links.
"""


# -- Schema HTML fixtures (Phase 3) --

SCHEMA_JSONLD_PRODUCT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Product Page</title>
</head>
<body>
    <h1>Test Product</h1>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Test Product",
        "description": "A sample product for testing",
        "offers": {
            "@type": "Offer",
            "price": "29.99",
            "priceCurrency": "USD"
        }
    }
    </script>
</body>
</html>"""

SCHEMA_MICRODATA_FAQ = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>FAQ Page</title></head>
<body>
    <div itemscope itemtype="http://schema.org/FAQPage">
        <div itemprop="mainEntity" itemscope itemtype="http://schema.org/Question">
            <h3 itemprop="name">What is this?</h3>
            <div itemprop="acceptedAnswer" itemscope itemtype="http://schema.org/Answer">
                <p itemprop="text">A test FAQ page.</p>
            </div>
        </div>
    </div>
</body>
</html>"""

SCHEMA_GRAPH_MULTI_TYPE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Multi-Type Page</title></head>
<body>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Product", "name": "Graph Product"},
            {"@type": "Organization", "name": "Graph Org"},
            {"@type": "WebSite", "name": "Graph Site"}
        ]
    }
    </script>
</body>
</html>"""

SCHEMA_RDFA_BREADCRUMB = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Breadcrumb Page</title></head>
<body>
    <ol vocab="http://schema.org/" typeof="BreadcrumbList">
        <li property="itemListElement" typeof="ListItem">
            <a property="item" typeof="WebPage" href="/">
                <span property="name">Home</span>
            </a>
            <meta property="position" content="1">
        </li>
    </ol>
</body>
</html>"""

SCHEMA_OG_PRODUCT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>OG Product Page</title>
    <meta property="og:type" content="product">
    <meta property="og:title" content="OG Product">
</head>
<body><p>Product with only OpenGraph markup.</p></body>
</html>"""

SCHEMA_MULTI_FORMAT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Multi-Format Page</title>
    <meta property="og:type" content="product">
</head>
<body>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "Test Article",
        "author": {"@type": "Person", "name": "Test Author"}
    }
    </script>
    <div itemscope itemtype="http://schema.org/FAQPage">
        <div itemprop="mainEntity" itemscope itemtype="http://schema.org/Question">
            <h3 itemprop="name">Q?</h3>
            <div itemprop="acceptedAnswer" itemscope itemtype="http://schema.org/Answer">
                <p itemprop="text">A.</p>
            </div>
        </div>
    </div>
    <ol vocab="http://schema.org/" typeof="BreadcrumbList">
        <li property="itemListElement" typeof="ListItem">
            <a property="item" typeof="WebPage" href="/"><span property="name">Home</span></a>
            <meta property="position" content="1">
        </li>
    </ol>
</body>
</html>"""

SCHEMA_MALFORMED_JSONLD = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Broken JSON-LD Page</title></head>
<body>
    <script type="application/ld+json">
    {broken json that will not parse
    </script>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Organization", "name": "Valid Org"}
    </script>
    <div itemscope itemtype="http://schema.org/FAQPage">
        <div itemprop="mainEntity" itemscope itemtype="http://schema.org/Question">
            <h3 itemprop="name">Still works?</h3>
            <div itemprop="acceptedAnswer" itemscope itemtype="http://schema.org/Answer">
                <p itemprop="text">Yes.</p>
            </div>
        </div>
    </div>
</body>
</html>"""

SCHEMA_EMPTY_HTML = "<html><head></head><body></body></html>"


# -- Fixtures for mock requests responses --

@pytest.fixture
def mock_success_response():
    """Return a mock requests.Response with 200 OK and valid HTML."""
    import requests
    resp = requests.Response()
    resp.status_code = 200
    resp.url = VALID_URL
    resp._content = VALID_HTML.encode('utf-8')
    return resp


@pytest.fixture
def mock_redirect_response():
    """Return a mock requests.Response that was redirected."""
    import requests
    resp = requests.Response()
    resp.status_code = 200
    resp.url = "https://example.com/final-destination"
    # history is populated by requests during actual redirect following;
    # for mock, we simulate the final state
    resp._content = VALID_HTML.encode('utf-8')
    return resp


@pytest.fixture
def mock_404_response():
    """Return a mock requests.Response with 404."""
    import requests
    resp = requests.Response()
    resp.status_code = 404
    resp.url = VALID_URL
    resp._content = b"<html><body>Not Found</body></html>"
    return resp


@pytest.fixture
def mock_500_response():
    """Return a mock requests.Response with 500."""
    import requests
    resp = requests.Response()
    resp.status_code = 500
    resp.url = VALID_URL
    resp._content = b"<html><body>Internal Server Error</body></html>"
    return resp


@pytest.fixture
def mock_response_map(
    mock_success_response,
    mock_redirect_response,
    mock_404_response,
    mock_500_response,
):
    """Convenience fixture: map of status scenario to mock response.

    Tests that need multiple mock responses can use this to avoid
    defining individual fixtures for each scenario.
    """
    return {
        'success': mock_success_response,
        'redirect': mock_redirect_response,
        '404': mock_404_response,
        '500': mock_500_response,
    }
