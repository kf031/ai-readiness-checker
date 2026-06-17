"""Tests for v3 LLM backend abstraction."""

import pytest
from checker.llm_backends import get_backend, OllamaBackend, OpenAIBackend, AnthropicBackend, BACKENDS


def test_backend_registry_complete():
    assert set(BACKENDS.keys()) == {"ollama", "openai", "anthropic"}


def test_get_backend_ollama():
    backend = get_backend("ollama", model="llama3.2:3b")
    assert isinstance(backend, OllamaBackend)
    assert backend.model == "llama3.2:3b"


def test_get_backend_openai():
    backend = get_backend("openai", model="gpt-4o-mini")
    assert isinstance(backend, OpenAIBackend)
    assert backend.model == "gpt-4o-mini"


def test_get_backend_anthropic():
    backend = get_backend("anthropic", model="claude-3-5-haiku-latest")
    assert isinstance(backend, AnthropicBackend)
    assert backend.model == "claude-3-5-haiku-latest"


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError, match="Unknown backend"):
        get_backend("nonexistent")


def test_get_backend_default_models():
    assert get_backend("ollama").model == "llama3.2:3b"
    assert get_backend("openai").model == "gpt-4o-mini"
    assert get_backend("anthropic").model == "claude-3-5-haiku-latest"


def test_fix_schema_with_backend():
    """fix-schema skill uses LLM backend when provided (mock)."""
    from unittest.mock import Mock
    from checker.skills.fix_schema import execute

    html = """<html><head><title>My Store</title></head>
    <body><h1>Buy Our Product</h1><p>Only $19.99. Free shipping worldwide.</p></body></html>"""
    report = {
        "modules": {
            "schema": {
                "score": 0.3,
                "types_found": [],
                "types_missing": ["Product", "Organization"],
            }
        }
    }

    mock_backend = Mock()
    mock_backend.generate.return_value = (
        "===SCHEMA_TYPE===Product\n"
        '<script type="application/ld+json">\n'
        '{"@context":"https://schema.org","@type":"Product","name":"Our Product"}\n'
        "</script>\n"
        "===END===\n"
        "===SCHEMA_TYPE===Organization\n"
        '<script type="application/ld+json">\n'
        '{"@context":"https://schema.org","@type":"Organization","name":"My Store"}\n'
        "</script>\n"
        "===END==="
    )

    result = execute(html=html, report=report, backend=mock_backend)

    assert len(result["changes"]) == 2
    assert "LLM-generated" in result["changes"][0]
    assert "Organization" in result["modified_html"]
    assert "Product" in result["modified_html"]
    assert result["target"] == "head"
    mock_backend.generate.assert_called_once()


def test_fix_schema_without_backend_uses_templates():
    """fix-schema skill falls back to templates when no backend."""
    from checker.skills.fix_schema import execute

    html = "<html><head></head><body></body></html>"
    report = {
        "modules": {
            "schema": {
                "score": 0.3,
                "types_found": [],
                "types_missing": ["FAQPage"],
            }
        }
    }

    result = execute(html=html, report=report)
    assert len(result["changes"]) == 1
    assert "template" in result["changes"][0]
    assert "FAQPage" in result["modified_html"]


# --- fix-headings with LLM backend ---

def test_fix_headings_with_backend():
    """fix-headings uses LLM to rewrite headings when backend provided."""
    from unittest.mock import Mock
    from checker.skills.fix_headings import execute

    html = """<html><body>
    <h1>Welcome</h1><h1>Also Welcome</h1>
    <h2>Details</h2><p>Content here.</p>
    </body></html>"""
    report = {
        "modules": {
            "content": {
                "headings": {
                    "score": 0.3,
                    "h1_count": 2,
                    "issues": ["Multiple H1s"],
                }
            }
        }
    }

    mock_backend = Mock()
    mock_backend.generate.return_value = (
        "<FIXED>\n<html><body>\n"
        "<h1>Welcome to Our Site</h1>\n"
        "<h2>Details</h2><p>Content here.</p>\n"
        "</body></html>\n"
        "</FIXED>"
    )

    result = execute(html=html, report=report, backend=mock_backend)
    assert len(result["changes"]) == 1
    assert "Multiple H1s" in result["changes"][0]
    assert result["target"] == "body"
    mock_backend.generate.assert_called_once()


def test_fix_headings_without_backend_falls_back():
    """fix-headings uses regex merge when no backend."""
    from checker.skills.fix_headings import execute

    html = "<html><body><h1>Welcome</h1><h1>Also Welcome</h1><h2>Details</h2></body></html>"
    report = {
        "modules": {
            "content": {
                "headings": {"score": 0.3, "h1_count": 2, "issues": ["Multiple H1s"]}
            }
        }
    }
    result = execute(html=html, report=report)
    assert len(result["changes"]) == 1
    assert "Merged" in result["changes"][0]


def test_fix_headings_no_issues_skips():
    """fix-headings returns no changes when no issues."""
    from checker.skills.fix_headings import execute

    html = "<html><body><h1>Welcome</h1></body></html>"
    report = {"modules": {"content": {"headings": {"score": 1.0, "issues": []}}}}
    result = execute(html=html, report=report)
    assert result["changes"] == []


# --- fix-readability with LLM backend ---

def test_fix_readability_with_backend():
    """fix-readability uses LLM to rewrite paragraphs when backend provided."""
    from unittest.mock import Mock
    from checker.skills.fix_readability import execute

    html = """<html><body>
    <p>This is a very long sentence that goes on and on and on and on for way too many words without any break in between whatsoever which makes it incredibly difficult to read and understand for the average reader on the web today.</p>
    </body></html>"""
    report = {
        "modules": {
            "content": {
                "readability": {"score": 0.2, "flesch_reading_ease": 25.0}
            }
        }
    }

    mock_backend = Mock()
    mock_backend.generate.return_value = (
        "This website has content that is difficult to read. "
        "We recommend breaking long sentences into shorter ones. "
        "This makes the text easier for most readers to understand."
    )

    result = execute(html=html, report=report, backend=mock_backend)
    assert len(result["changes"]) == 1
    assert "Rewrote" in result["changes"][0]
    assert "paragraph" in result["changes"][0].lower()
    mock_backend.generate.assert_called_once()


# --- fix-qa with LLM backend ---

def test_fix_qa_with_backend():
    """fix-qa uses LLM to generate real Q&A when backend provided."""
    from unittest.mock import Mock
    from checker.skills.fix_qa import execute

    html = """<html><body><h1>Our SaaS Product</h1>
    <p>We offer the best project management software. Plans start at $29/month.
    Our software helps teams collaborate, track progress, and deliver on time.</p>
    </body></html>"""
    report = {
        "modules": {
            "content": {
                "qa_density": {"score": 0.1, "question_count": 0}
            }
        }
    }

    mock_backend = Mock()
    mock_backend.generate.return_value = """
<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
  <h3 itemprop="name">What is Our SaaS Product?</h3>
  <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
    <p itemprop="text">It's a project management tool for team collaboration.</p>
  </div>
</div>"""

    result = execute(html=html, report=report, backend=mock_backend)
    assert len(result["changes"]) == 1
    assert "AI-generated" in result["changes"][0]
    assert "schema.org/Question" in result["modified_html"]
    mock_backend.generate.assert_called_once()


# --- fix-llms-txt with LLM backend ---

def test_fix_llms_txt_with_backend():
    """fix-llms-txt uses LLM to generate llms.txt when backend provided."""
    from unittest.mock import Mock
    from checker.skills.fix_llms_txt import execute

    html = """<html><head><title>My Site</title></head>
    <body><h1>My Site</h1><h2>About</h2><p>We do cool things.</p>
    <a href="/about">About Us</a><a href="/pricing">Pricing</a></body></html>"""
    report = {
        "url": "https://mysite.com",
        "modules": {
            "llms_txt": {"score": 0.0}
        }
    }

    mock_backend = Mock()
    mock_backend.generate.return_value = """# My Site
> We do cool things and help teams succeed

## About
- [About Us](/about): Learn about our team and mission
- [Pricing](/pricing): Plans starting at $29/month

## Overview
My Site is a platform that helps teams collaborate and track projects."""

    result = execute(html=html, report=report, backend=mock_backend)
    assert len(result["changes"]) == 1
    assert "AI-powered" in result["changes"][0]
    mock_backend.generate.assert_called_once()
