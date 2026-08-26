import logging
import time
from dataclasses import dataclass

import httpx

from app.config import Settings
from app.models import Citation


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResult:
    content: str | None
    provider_used: str
    fallback_used: bool
    error_type: str | None
    latency_ms: int


class LLMClient:
    """OpenAI-compatible 适配器；云端异常时返回结构化降级信息。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def mode(self) -> str:
        return "demo" if self.settings.demo_mode else "cloud"

    async def complete(
        self, system_prompt: str, user_prompt: str, citations: list[Citation]
    ) -> LLMResult:
        started = time.perf_counter()
        if self.settings.demo_mode:
            return LLMResult(None, "demo", True, None, 0)
        context = "\n\n".join(
            f"[{item.chunk_id}] {item.source}\n{item.chunk}" for item in citations
        )
        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_prompt}\n\n可用资料：\n{context}"},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        url = f'{self.settings.llm_base_url.rstrip("/")}/chat/completions'
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
                content = body.get("choices", [{}])[0].get("message", {}).get("content")
                latency_ms = round((time.perf_counter() - started) * 1000)
                if isinstance(content, str) and content.strip():
                    return LLMResult(content.strip(), "cloud", False, None, latency_ms)
                logger.warning("LLM returned no usable content: %s", body)
                return LLMResult(None, "cloud", True, "empty_response", latency_ms)
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning("LLM request failed; using deterministic fallback: %s", exc)
            return LLMResult(
                None,
                "cloud",
                True,
                type(exc).__name__,
                round((time.perf_counter() - started) * 1000),
            )
