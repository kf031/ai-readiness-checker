"""V3 standalone LLM backends — abstracted behind a common interface.

Supported backends:
    - ollama: Local LLM via Ollama (recommended: llama3.2:3b)
    - openai: OpenAI API (gpt-4o-mini, etc.)
    - anthropic: Anthropic API (claude-3-5-haiku, etc.)

Usage:
    from checker.llm_backends import get_backend, LLMBackend
    backend = get_backend("ollama", model="llama3.2:3b")
    result = backend.generate("Fix this HTML", system="You are an SEO expert.")
"""

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Abstract interface for LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, system: str = "") -> str:
        """Generate text from the LLM.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.

        Returns:
            The generated text response.
        """
        ...


class OllamaBackend(LLMBackend):
    """Backend for local Ollama models.

    Requires: pip install ollama
    Requires: ollama serve running locally (default: http://localhost:11434)
    """

    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self._client = None
        self._available = True

    @property
    def client(self):
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self.host)
            except Exception:
                self._available = False
                raise RuntimeError(
                    "Ollama is not running or not installed. "
                    "Install with: pip install ollama. "
                    "Start with: ollama serve"
                )
        return self._client

    def generate(self, prompt: str, system: str = "") -> str:
        if not self._available:
            return ""

        try:
            response = self.client.chat(
                model=self.model,
                messages=_build_messages(prompt, system),
            )
            return response["message"]["content"]
        except Exception:
            return ""


class OpenAIBackend(LLMBackend):
    """Backend for OpenAI API.

    Requires: pip install openai
    Requires: OPENAI_API_KEY environment variable or api_key parameter.
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self.api_key = api_key
        self._client = None
        self._available = True

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except Exception:
                self._available = False
                raise RuntimeError(
                    "OpenAI client failed to initialize. "
                    "Install with: pip install openai. "
                    "Set OPENAI_API_KEY environment variable."
                )
        return self._client

    def generate(self, prompt: str, system: str = "") -> str:
        if not self._available:
            return ""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=_build_messages(prompt, system),
            )
            return response.choices[0].message.content or ""
        except Exception:
            return ""


class AnthropicBackend(LLMBackend):
    """Backend for Anthropic API.

    Requires: pip install anthropic
    Requires: ANTHROPIC_API_KEY environment variable or api_key parameter.
    """

    def __init__(self, model: str = "claude-3-5-haiku-latest", api_key: str | None = None):
        self.model = model
        self.api_key = api_key
        self._client = None
        self._available = True

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self._available = False
                raise RuntimeError(
                    "Anthropic client failed to initialize. "
                    "Install with: pip install anthropic. "
                    "Set ANTHROPIC_API_KEY environment variable."
                )
        return self._client

    def generate(self, prompt: str, system: str = "") -> str:
        if not self._available:
            return ""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception:
            return ""


def _build_messages(prompt: str, system: str = "") -> list[dict]:
    """Build message list for OpenAI/Ollama chat format."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


# Registry of available backends
BACKENDS = {
    "ollama": OllamaBackend,
    "openai": OpenAIBackend,
    "anthropic": AnthropicBackend,
}


def get_backend(name: str, **kwargs) -> LLMBackend:
    """Factory: get an LLM backend by name.

    Args:
        name: "ollama", "openai", or "anthropic".
        **kwargs: Passed to the backend constructor (e.g., model, api_key).

    Returns:
        An LLMBackend instance.

    Raises:
        ValueError: If the backend name is unknown.
    """
    backend_cls = BACKENDS.get(name)
    if backend_cls is None:
        raise ValueError(f"Unknown backend: {name}. Available: {', '.join(BACKENDS)}")
    return backend_cls(**kwargs)
