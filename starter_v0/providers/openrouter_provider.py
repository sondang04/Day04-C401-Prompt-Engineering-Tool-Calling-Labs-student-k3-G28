from __future__ import annotations

import os

from providers.openai_provider import OpenAIProvider


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter Free Models Router - OpenAI-compatible with optimized free tier config."""

    # Free tier requires HTTP-Referer and X-Title headers
    SITE_URL = os.getenv("OPENROUTER_SITE_URL", "https://github.com/openrouter/free")
    SITE_NAME = os.getenv("OPENROUTER_SITE_NAME", "Research Agent")

    # Recommended free models optimized for tool calling
    FREE_MODELS = [
        "google/gemma-4-31b-it",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3-8b-instruct",
        "mistralai/mistral-7b-instruct",
        "google/gemma-2-9b-it",
    ]
    # Default fallback model for free tier
    DEFAULT_MODEL = "google/gemma-4-31b-it"

    def __init__(self) -> None:
        super().__init__(
            api_key_env="OPENROUTER_API_KEY",
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_model=self.DEFAULT_MODEL,
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        tool_choice: str | None = None,
    ) -> "ModelResponse":
        """Override to add OpenRouter-specific headers for free tier."""
        from openai import OpenAI

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing API key env var: {self.api_key_env}")

        client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": self.SITE_URL,
                "X-Title": self.SITE_NAME,
            },
        )

        kwargs: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice

        resp = client.chat.completions.create(**kwargs)
        import json

        from providers.base import ModelResponse, ToolCall

        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for call in msg.tool_calls or []:
            args = json.loads(call.function.arguments or "{}")
            calls.append(ToolCall(name=call.function.name, args=args))
        return ModelResponse(text=msg.content, tool_calls=calls, raw=resp)
