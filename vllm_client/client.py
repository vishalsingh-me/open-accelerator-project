"""vLLM HTTP client using the OpenAI-compatible API."""

import logging
import os
import time

from openai import OpenAI

logger = logging.getLogger(__name__)


class VLLMClient:
    """Singleton vLLM client for large and draft completion endpoints."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self.__class__._initialized:
            return

        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
        self.large_model = os.getenv(
            "VLLM_LARGE_MODEL", "meta-llama/Llama-3.1-70B-Instruct"
        )
        self.draft_model = os.getenv(
            "VLLM_DRAFT_MODEL", "meta-llama/Llama-3.2-3B-Instruct"
        )
        self._client = OpenAI(base_url=self.base_url, api_key="EMPTY")
        self.__class__._initialized = True

    def complete_large(
        self, prompt: str, max_tokens: int = 1024, temperature: float = 0.1
    ) -> str:
        """Generate text with the large model endpoint."""
        return self._complete(
            model=self.large_model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def complete_draft(
        self, prompt: str, max_tokens: int = 512, temperature: float = 0.2
    ) -> str:
        """Generate text with the draft model endpoint."""
        return self._complete(
            model=self.draft_model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _complete(
        self, model: str, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", 0) if usage else 0
        # Self-hosted vLLM usually has no metered per-token charge.
        cost_estimate_usd = 0.0

        logger.info(
            "vLLM completion | model=%s | latency_ms=%.2f | tokens=%s | cost_estimate_usd=%.6f",
            model,
            latency_ms,
            total_tokens,
            cost_estimate_usd,
        )

        message = response.choices[0].message.content if response.choices else ""
        return message or ""
