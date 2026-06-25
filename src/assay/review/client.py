# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Provider-neutral LLM client for the code-review reviewers.

`LLMClient` is the abstraction the runner depends on: given a system prompt and a user
prompt, return the model's text response. The Anthropic-backed default is opt-in behind the
`review` optional extra and is constructed lazily so that importing this module never touches
the `anthropic` SDK or a network. Tests inject a deterministic fake instead.

If the optional dependency or an API key is missing, `AnthropicLLMClient` raises
`LLMClientError` with an actionable message rather than crashing at an arbitrary call site.
"""

from __future__ import annotations

import os
from typing import Optional, Protocol, runtime_checkable

DEFAULT_MODEL = "claude-opus-4-8"
_API_KEY_ENV = "ANTHROPIC_API_KEY"


class LLMClientError(Exception):
    """Raised when an LLM client cannot be constructed or invoked.

    Notably raised (with an actionable message) when the optional `anthropic` dependency or an
    API key is absent — code review is opt-in, so this is a clear configuration error, never a
    bare ImportError or AttributeError at an arbitrary call site.
    """


@runtime_checkable
class LLMClient(Protocol):
    """A minimal single-turn text completion interface.

    The runner only needs to send a system + user prompt and read back text; keeping the
    surface this small lets tests pass a trivial deterministic fake.
    """

    def complete(self, system: str, prompt: str) -> str:
        """Return the model's text response to `prompt` under the `system` instruction."""
        ...


class AnthropicLLMClient:
    """Anthropic-backed `LLMClient` (opt-in via the `review` extra).

    Determinism: no sampling parameters are sent. Opus 4.8 removed `temperature`/`top_p`/`top_k`
    (sending them is a 400), so reproducibility comes from a fixed model + fixed prompts +
    low effort, not a temperature. Output is constrained to the final answer (thinking left at
    its default omitted display) so reviewers return parseable JSON.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,  # noqa: UP007
        max_tokens: int = 4096,
        client: Optional[object] = None,  # noqa: UP007  # pre-built anthropic.Anthropic, if any
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = client
        self._api_key = api_key or os.environ.get(_API_KEY_ENV)

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise LLMClientError(
                "code review requires the optional 'anthropic' dependency. "
                "Install it with: pip install 'assay-kit[review]'"
            ) from exc
        if not self._api_key:
            raise LLMClientError(
                f"code review requires an Anthropic API key. Set the {_API_KEY_ENV} "
                "environment variable or pass api_key=."
            )
        self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, system: str, prompt: str) -> str:
        client = self._ensure_client()
        response = client.messages.create(  # type: ignore[attr-defined]
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        parts: list[str] = []
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", None) == "text":
                parts.append(str(getattr(block, "text", "")))
        return "".join(parts)
