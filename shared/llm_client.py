"""Shared compatibility LLM client used by services that import `shared.llm_client`."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    """Minimal config for OpenAI-compatible chat completions."""

    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-4")
    max_tokens: int = Field(default=2000)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    timeout: int = Field(default=60)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int = 2000
    response_format: Optional[dict[str, Any]] = None


class LLMError(Exception):
    """Raised when the LLM request or JSON parsing fails."""


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("LLM_MODEL", "gpt-4"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
            timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        )
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[ChatMessage | dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        formatted_messages = [
            ChatMessage(**message) if isinstance(message, dict) else message
            for message in messages
        ]

        request = ChatCompletionRequest(
            model=model or self.config.model,
            messages=formatted_messages,
            temperature=self.config.temperature if temperature is None else temperature,
            max_tokens=self.config.max_tokens if max_tokens is None else max_tokens,
            response_format={"type": "json_object"} if json_mode else None,
        )

        try:
            response = await self.client.post(
                "/chat/completions",
                json=request.model_dump(exclude_none=True),
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            logger.error("LLM request timed out: %s", exc)
            raise LLMError("LLM request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("LLM HTTP error %s: %s", exc.response.status_code, exc.response.text)
            raise LLMError(f"LLM request failed: {exc.response.status_code}") from exc
        except Exception as exc:
            logger.error("LLM request failed: %s", exc)
            raise LLMError(f"LLM request failed: {exc}") from exc

    async def parse_json(
        self,
        messages: list[ChatMessage | dict[str, Any]],
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=0.0,
            json_mode=True,
        )

        try:
            content = response["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, json.JSONDecodeError) as exc:
            logger.error("Failed to parse LLM response: %s", exc)
            raise LLMError(f"LLM response parsing failed: {exc}") from exc


_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def close_llm_client() -> None:
    global _llm_client
    if _llm_client is not None:
        await _llm_client.close()
        _llm_client = None


__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "ChatMessage",
    "get_llm_client",
    "close_llm_client",
]
