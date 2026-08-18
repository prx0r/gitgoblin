from __future__ import annotations

import os
from typing import Any

import httpx


class OpenAICompatibleAnalyzer:
    """Optional enrichment layer. Deterministic scoring never depends on this class."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("GITGOBLIN_LLM_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("GITGOBLIN_LLM_API_KEY")
        self.model = model or os.getenv("GITGOBLIN_LLM_MODEL")
        if not (self.base_url and self.api_key and self.model):
            raise ValueError("Set GITGOBLIN_LLM_BASE_URL, GITGOBLIN_LLM_API_KEY, and GITGOBLIN_LLM_MODEL")

    def analyze_architecture(self, context: str) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Extract architecture primitives, constraints, likely downstream applications, and falsifiable tests. "
                            "Never invent repository behavior not present in the supplied context."
                        ),
                    },
                    {"role": "user", "content": context[:30000]},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
