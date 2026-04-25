from __future__ import annotations

import os
import time
from typing import Any

import requests


class LLMReasoner:
    def __init__(self) -> None:
        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1").rstrip("/")
        self.model = os.getenv("VLLM_MODEL", "")
        self.api_key = os.getenv("VLLM_API_KEY", os.getenv("COMPATIBLE_API_KEY", "")).strip()
        self.timeout = float(os.getenv("VLLM_TIMEOUT", "4"))
        self._status_checked = False
        self._is_available = False
        self._banner_printed = False

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def _check_endpoint(self) -> bool:
        if self._status_checked:
            return self._is_available

        self._status_checked = True

        # probe models endpoint first
        try:
            resp = requests.get(
                f"{self.base_url}/models",
                timeout=self.timeout,
                headers=self._headers(),
            )
            if resp.ok:
                self._is_available = True
                return True
        except Exception:
            pass

        # fallback probe chat endpoint with tiny payload
        payload = {
            "model": self.model or "dummy",
            "messages": [{"role": "user", "content": "health_check"}],
            "max_tokens": 4,
            "temperature": 0,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=self.timeout,
                headers=self._headers(),
            )
            if resp.ok:
                self._is_available = True
                return True
        except Exception:
            pass

        self._is_available = False
        return False

    def reason(self, prompt: str) -> dict[str, Any]:
        start = time.perf_counter()

        endpoint_available = self._check_endpoint()
        if endpoint_available and self.model:
            if not self._banner_printed:
                print("vLLM endpoint detected: using vLLM reasoning")
                self._banner_printed = True
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are IncidentIQ Autopilot verifier. Return concise operational "
                            "reasoning and a safe recommendation."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 220,
            }
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=self.timeout,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                body = resp.json()
                content = body["choices"][0]["message"]["content"]
                latency = time.perf_counter() - start
                return {
                    "source": "vllm",
                    "reasoning": content.strip(),
                    "latency": latency,
                }
            except Exception as exc:
                fallback = self._local_fallback(prompt)
                latency = time.perf_counter() - start
                fallback.update(
                    {
                        "source": "local_fallback",
                        "latency": latency,
                        "error": f"vLLM request failed: {exc}",
                    }
                )
                return fallback

        if endpoint_available and not self.model and not self._banner_printed:
            print("vLLM endpoint detected but VLLM_MODEL is unset: using local fallback reasoning")
            self._banner_printed = True
        elif not endpoint_available and not self._banner_printed:
            print("vLLM unavailable: using local fallback reasoning")
            self._banner_printed = True

        fallback = self._local_fallback(prompt)
        latency = time.perf_counter() - start
        fallback.update({"source": "local_fallback", "latency": latency})
        return fallback

    @staticmethod
    def _local_fallback(prompt: str) -> dict[str, Any]:
        brief = (
            "Local reasoning fallback: prioritize service restoration for Tier 1 failures; "
            "block Tier 2 actions behind approval and shadow simulation."
        )
        return {"reasoning": f"{brief}\nPrompt digest: {prompt[:180]}"}
