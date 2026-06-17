"""Tests for v3 LLM backend abstraction."""

import pytest
from src.checker.llm_backends import get_backend, OllamaBackend, OpenAIBackend, AnthropicBackend, BACKENDS


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
    from src.checker.skills.fix_schema import execute

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
    from src.checker.skills.fix_schema import execute

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
