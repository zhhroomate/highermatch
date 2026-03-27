"""
HigherMatch™ Candidate Service - LLM Client
============================================

统一的 LLM API 客户端，支持 OpenAI 格式接口。
用于简历解析等 AI 功能。

版本: 1.0.0
"""

import json
import logging
from typing import Optional, Any
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== LLM 配置 ====================
class LLMConfig(BaseModel):
    """LLM 配置"""
    api_key: str = Field(default="", description="API 密钥")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="API 基础 URL"
    )
    model: str = Field(default="gpt-4", description="模型名称")
    max_tokens: int = Field(default=2000, description="最大 token 数")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="温度参数")
    timeout: int = Field(default=60, description="超时时间(秒)")


# ==================== LLM 请求/响应模型 ====================
class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="角色: system, user, assistant")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    """聊天补全请求"""
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int = 2000
    response_format: Optional[dict] = None  # {"type": "json_object"}


class ChatCompletionChoice(BaseModel):
    """聊天补全选项"""
    index: int
    message: ChatMessage
    finish_reason: str


class UsageInfo(BaseModel):
    """用量信息"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """聊天补全响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo


# ==================== LLM 客户端 ====================
class LLMClient:
    """
    LLM API 客户端

    支持 OpenAI 格式的 Chat API，用于简历解析和内容生成。
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 LLM 客户端

        Args:
            config: LLM 配置，如果不提供则从环境变量加载
        """
        if config is None:
            config = LLMConfig(
                api_key=_get_env("OPENAI_API_KEY", ""),
                base_url=_get_env("LLM_BASE_URL", "https://api.openai.com/v1"),
                model=_get_env("LLM_MODEL", "gpt-4"),
                max_tokens=int(_get_env("LLM_MAX_TOKENS", "2000")),
                temperature=float(_get_env("LLM_TEMPERATURE", "0.0")),
                timeout=int(_get_env("LLM_TIMEOUT", "60")),
            )
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端 (懒加载)"""
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
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[ChatMessage | dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> dict:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            model: 模型名称 (可选，覆盖默认)
            temperature: 温度参数 (可选)
            max_tokens: 最大 token 数 (可选)
            json_mode: 是否返回 JSON 格式

        Returns:
            API 响应字典

        Raises:
            LLMError: 请求失败时抛出
        """
        # 转换消息格式
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(ChatMessage(**msg))
            else:
                formatted_messages.append(msg)

        # 构建请求
        request = ChatCompletionRequest(
            model=model or self.config.model,
            messages=formatted_messages,
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            response_format={"type": "json_object"} if json_mode else None,
        )

        try:
            response = await self.client.post(
                "/chat/completions",
                json=request.model_dump(exclude_none=True),
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"LLM request timeout: {e}")
            raise LLMError("LLM 请求超时")
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"LLM 请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise LLMError(f"LLM 请求失败: {str(e)}")

    async def parse_json(
        self,
        messages: list[ChatMessage | dict],
        model: Optional[str] = None,
    ) -> dict:
        """
        发送 JSON 解析请求

        专门用于需要结构化 JSON 输出的场景，如简历解析。

        Args:
            messages: 消息列表
            model: 模型名称 (可选)

        Returns:
            解析后的 JSON 字典

        Raises:
            LLMError: 解析失败时抛出
        """
        response = await self.chat(
            messages=messages,
            model=model,
            temperature=0.0,
            json_mode=True,
        )

        # 提取内容
        try:
            content = response["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise LLMError(f"LLM 响应解析失败: {str(e)}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        简单的文本生成

        Args:
            prompt: 用户提示
            system_prompt: 系统提示 (可选)
            **kwargs: 其他参数传递给 chat

        Returns:
            生成的文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.chat(messages, **kwargs)
        return response["choices"][0]["message"]["content"]


# ==================== 错误类 ====================
class LLMError(Exception):
    """LLM 相关错误"""
    pass


# ==================== 辅助函数 ====================
def _get_env(key: str, default: str = "") -> str:
    """获取环境变量"""
    import os
    return os.getenv(key, default)


# ==================== 全局客户端实例 ====================
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


async def close_llm_client() -> None:
    """关闭全局 LLM 客户端"""
    global _llm_client
    if _llm_client is not None:
        await _llm_client.close()
        _llm_client = None


# ==================== 导出 ====================
__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "ChatMessage",
    "get_llm_client",
    "close_llm_client",
]
