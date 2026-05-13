"""Shared fixtures for AI Readiness Checker tests."""

from datetime import datetime, timezone

import pytest
from bs4 import BeautifulSoup


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


# -- Content HTML fixtures (Phase 4) --

CONTENT_HTML_TEXT_HEAVY = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Text-Heavy Article Page</title>
    <meta name="description" content="A comprehensive article about web accessibility and AI search engine optimization best practices">
</head>
<body>
    <h1>The Complete Guide to AI Search Engine Visibility</h1>
    <p>Artificial intelligence search engines are transforming how users discover content online. These systems rely on structured data, readable text, and clear content organization to surface the most relevant results.</p>
    <p>Web accessibility and AI readiness share many common principles. Both prioritize semantic HTML structure, descriptive headings, and high-quality textual content that clearly communicates the purpose of each page.</p>
    <p>Modern websites must balance visual design with machine readability. Search engines and AI crawlers analyze content differently than human readers, making it essential to optimize for both audiences simultaneously.</p>
    <p>The relationship between content quality and search visibility continues to evolve as language models become more sophisticated at understanding natural language patterns and contextual relationships within web documents.</p>
    <h2>Understanding Structured Data</h2>
    <p>Schema.org markup provides a standardized vocabulary for describing page content to machines. When implemented correctly, structured data helps AI systems understand product information, FAQs, organizational details, and article metadata.</p>
    <p>Google processes millions of web pages daily using automated extraction algorithms that identify key entities like organizations, products, and people mentioned throughout the content.</p>
    <h2>Content Quality Metrics</h2>
    <p>Readability scores measure how accessible your writing is to a general audience. The Flesch Reading Ease formula evaluates sentence length and syllable count to produce a score between 0 and 100, with higher scores indicating easier reading.</p>
    <p>The Gunning Fog Index estimates the years of formal education needed to understand text on first reading. Business content typically targets a Fog score between 8 and 12.</p>
</body>
</html>"""

CONTENT_HTML_FAQ = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Frequently Asked Questions</title>
</head>
<body>
    <h1>Frequently Asked Questions</h1>
    <h2>What is AI search engine visibility?</h2>
    <p>AI search engine visibility measures how easily artificial intelligence crawlers can discover, understand, and surface your website content in response to user queries.</p>
    <h2>How do I check my site's AI readiness?</h2>
    <p>You can use automated tools that analyze your robots.txt configuration, structured data markup, content readability, and other signals that AI crawlers use to evaluate web pages.</p>
    <h2>Why does heading structure matter for AI?</h2>
    <p>Clear heading hierarchies help AI models understand the organization of your content. They identify main topics and subtopics, making it easier to extract relevant information.</p>
    <h2>Can AI crawlers read JavaScript content?</h2>
    <p>Some AI crawlers can execute JavaScript, but many rely on server-rendered HTML. It is best practice to ensure critical content is available in the initial HTML response.</p>
    <p>For more detailed guidance, consult the documentation provided by major AI companies about their crawler behavior and requirements.</p>
</body>
</html>"""

CONTENT_HTML_THIN = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Thin Content</title>
    <script src="/assets/bundle.12345.js"></script>
    <link rel="stylesheet" href="/styles/main.css">
    <link rel="preload" href="/fonts/inter.woff2" as="font">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#ffffff">
    <meta property="og:title" content="Thin Content">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary">
</head>
<body>
    <div id="root"></div>
    <script>window.__INITIAL_STATE__ = {};</script>
</body>
</html>"""

CONTENT_HTML_NO_HEADINGS = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>No Headings Page</title>
</head>
<body>
    <p>This page contains paragraphs of text but no heading elements at all.</p>
    <p>The absence of headings makes it difficult for AI crawlers to understand the document structure.</p>
    <p>Search engines may struggle to identify the main topics and content hierarchy on pages without proper heading markup.</p>
    <p>Best practices recommend using H1 for the main page title, H2 for major sections, and H3 for subsections within those sections.</p>
</body>
</html>"""

CONTENT_HTML_MULTI_ENTITY = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Multi-Entity Company Page</title>
</head>
<body>
    <h1>About Our Company</h1>
    <p>Apple Inc. announced a new partnership with Microsoft Corporation to develop cross-platform AI solutions. The collaboration was revealed by Tim Cook during a press conference in Cupertino, California.</p>
    <p>Google DeepMind researchers based in London, United Kingdom have published groundbreaking research on natural language understanding. The team at OpenAI in San Francisco continues to advance the field of artificial intelligence.</p>
    <p>NVIDIA Corporation, headquartered in Santa Clara, provides GPU hardware essential for training large language models. Amazon Web Services and Google Cloud Platform both offer managed AI infrastructure services.</p>
    <p>International Business Machines has a long history of AI research dating back to the Deep Blue chess computer. Modern IBM Watson services are used by healthcare organizations across the United States and Europe.</p>
</body>
</html>"""


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


# -- Orchestrator fixtures (Phase 6) --

@pytest.fixture
def sample_fetch_result():
    """Return a valid FetchResult for orchestrator tests."""
    from src.checker.contracts import FetchResult

    html = "<html><body><p>Test</p></body></html>"
    return FetchResult(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        html=html,
        soup=BeautifulSoup(html, 'lxml'),
    )


@pytest.fixture
def sample_robots_result():
    """Return a valid RobotsResult for orchestrator tests."""
    from src.checker.contracts import RobotsResult

    return RobotsResult(
        url="https://example.com",
        exists=True,
        bots=[],
    )


@pytest.fixture
def sample_llms_result():
    """Return a valid LlmsResult for orchestrator tests."""
    from src.checker.contracts import LlmsResult

    return LlmsResult(
        url="https://example.com",
        found=False,
    )


@pytest.fixture
def sample_schema_analysis():
    """Return a valid SchemaAnalysis for orchestrator tests."""
    from src.checker.contracts import SchemaAnalysis

    return SchemaAnalysis(
        url="https://example.com",
        score=0.5,
        detected_types={"Organization"},
    )


@pytest.fixture
def sample_content_analysis():
    """Return a valid ContentAnalysis for orchestrator tests."""
    from src.checker.contracts import ContentAnalysis

    return ContentAnalysis(
        url="https://example.com",
        combined_score=0.6,
    )


@pytest.fixture
def sample_crawl_error():
    """Return a CrawlError for orchestrator tests."""
    from src.checker.contracts import CrawlError

    return CrawlError(
        url="https://example.com",
        error_type="timeout",
        message="timed out after 10s",
    )


# -- Dashboard fixtures (Phase 7) --

@pytest.fixture
def sample_score_report():
    """Return a complete ScoreReport for dashboard tests."""
    from src.checker.contracts import ScoreReport

    return ScoreReport(
        url="https://example.com",
        overall_score=78.5,
        grade="B",
        module_breakdown={
            "robots": {"score": 0.85, "weight": 0.20, "weighted": 17.0},
            "llms_txt": {"score": 1.00, "weight": 0.15, "weighted": 15.0},
            "schema": {"score": 0.60, "weight": 0.30, "weighted": 18.0},
            "content": {"score": 0.72, "weight": 0.35, "weighted": 25.2},
        },
        recommendations=[
            {"priority": "HIGH", "module": "robots", "message": "GPTBot is blocked in your robots.txt"},
            {"priority": "MEDIUM", "module": "schema", "message": "No FAQPage schema found"},
            {"priority": "LOW", "module": "content", "message": "Add more descriptive H2 headings"},
        ],
    )


@pytest.fixture
def mock_pipeline_result(sample_score_report,
                          sample_robots_result, sample_llms_result,
                          sample_schema_analysis, sample_content_analysis):
    """Return a full 8-key pipeline result dict matching the updated orchestrator return shape."""
    return {
        "report": sample_score_report,
        "errors": [],
        "complete": True,
        "stages_run": ["crawl", "access_signals", "schema", "content", "score"],
        "robots_result": sample_robots_result,
        "llms_result": sample_llms_result,
        "schema_analysis": sample_schema_analysis,
        "content_analysis": sample_content_analysis,
    }
