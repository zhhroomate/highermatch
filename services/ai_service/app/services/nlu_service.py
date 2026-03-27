"""
HigherMatch™ AI Service - NLU Service
======================================

自然语言理解服务，用于解析用户输入的招聘需求。

提供:
- 自然语言职位需求解析
- 结构化 JSON 输出
- Redis 缓存
- LLM 重试机制

版本: 1.0.0
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as redis

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 配置常量 ====================

# Redis 缓存配置
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# NLU 缓存配置
NLU_CACHE_PREFIX = "nlu:"
NLU_CACHE_TTL = 3600  # 1小时

# LLM 配置
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-plus")
LLM_API_BASE = os.getenv(
    "LLM_API_BASE",
    os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)

# System Prompt 路径
SYSTEM_PROMPT_PATH = os.getenv(
    "NLU_SYSTEM_PROMPT_PATH",
    "/app/prompts/nlu_system_prompt.txt"
)


# ==================== Pydantic 模型 ====================

from pydantic import BaseModel, Field


class JobRequirementDraft(BaseModel):
    """职位需求草稿"""

    job_title: Optional[str] = Field(default=None, description="职位名称")
    skills: list[str] = Field(default_factory=list, description="技能列表", max_length=10)
    years_exp_min: Optional[int] = Field(default=0, ge=0, description="最低工作年限")
    years_exp_max: Optional[int] = Field(default=None, ge=0, description="最高工作年限")
    location: list[str] = Field(default_factory=list, description="工作地点列表", max_length=5)
    salary_min: Optional[int] = Field(default=None, ge=0, description="最低薪资 (元/月)")
    salary_max: Optional[int] = Field(default=None, ge=0, description="最高薪资 (元/月)")
    industry: Optional[str] = Field(default=None, description="行业")


class ConfidenceScores(BaseModel):
    """各字段置信度"""

    job_title: float = Field(..., ge=0.0, le=1.0, description="职位名称置信度")
    skills: float = Field(..., ge=0.0, le=1.0, description="技能置信度")
    years_exp: float = Field(..., ge=0.0, le=1.0, description="工作年限置信度")
    location: float = Field(..., ge=0.0, le=1.0, description="工作地点置信度")
    salary: float = Field(..., ge=0.0, le=1.0, description="薪资置信度")
    industry: float = Field(..., ge=0.0, le=1.0, description="行业置信度")


class ClarificationQuestion(BaseModel):
    """澄清问题"""

    field: str = Field(..., description="需要澄清的字段")
    question: str = Field(..., description="自然语言问题")
    reason: str = Field(..., description="为什么需要澄清")


class NLUParseResponse(BaseModel):
    """NLU 解析响应"""

    job_requirement_draft: JobRequirementDraft = Field(..., description="职位需求草稿")
    confidence_scores: ConfidenceScores = Field(..., description="各字段置信度")
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="澄清问题列表"
    )


class NLUError(BaseModel):
    """NLU 错误"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(default=None, description="附加详情")


# ==================== Redis 客户端 ====================


class RedisCache:
    """
    Redis 缓存客户端

    用于缓存 NLU 解析结果。
    """

    def __init__(self) -> None:
        """初始化 Redis 客户端"""
        self._client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """连接到 Redis"""
        try:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self._client.ping()
            self._connected = True
            logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False

    async def disconnect(self) -> None:
        """断开 Redis 连接"""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[str]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或 None
        """
        if not self._connected or not self._client:
            return None

        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int = NLU_CACHE_TTL,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间 (秒)

        Returns:
            True: 设置成功
        """
        if not self._connected or not self._client:
            return False

        try:
            await self._client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected


# 全局 Redis 客户端
_cache: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """获取 Redis 缓存客户端"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
        await _cache.connect()
    return _cache


async def close_cache() -> None:
    """关闭 Redis 缓存"""
    global _cache
    if _cache:
        await _cache.disconnect()
        _cache = None


# ==================== LLM 客户端 ====================


class LLMClient:
    """
    LLM 客户端

    封装 LLM API 调用，包含超时和重试机制。
    """

    def __init__(
        self,
        api_key: str,
        model: str = LLM_MODEL,
        api_base: str = LLM_API_BASE,
        timeout: float = LLM_TIMEOUT,
        max_retries: int = LLM_MAX_RETRIES,
    ) -> None:
        """
        初始化 LLM 客户端

        Args:
            api_key: API 密钥
            model: 模型名称
            api_base: API 基础 URL
            timeout: 超时时间 (秒)
            max_retries: 最大重试次数
        """
        self.api_key = api_key
        self.model = model
        self.api_base = api_base
        self.timeout = timeout
        self.max_retries = max_retries

    def _generate_cache_key(self, text: str) -> str:
        """
        生成缓存键

        Args:
            text: 输入文本

        Returns:
            缓存键
        """
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        return f"{NLU_CACHE_PREFIX}{text_hash}"

    def _normalize_salary(self, value: Any) -> Optional[int]:
        """
        规范化薪资值

        Args:
            value: 原始值

        Returns:
            规范化后的整数薪资
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return int(value) if value >= 0 else None

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            # 移除货币符号和空格
            value = re.sub(r"[¥$元/月万千\s]", "", value)

            # 处理 "15K", "15k", "15万" 等格式
            if "万" in value:
                try:
                    return int(float(value.replace("万", "")) * 10000)
                except ValueError:
                    return None
            elif "k" in value.lower():
                try:
                    return int(float(value.lower().replace("k", "")) * 1000)
                except ValueError:
                    return None
            else:
                try:
                    return int(float(value))
                except ValueError:
                    return None

        return None

    async def call_llm(
        self,
        system_prompt: str,
        user_message: str,
    ) -> dict:
        """
        调用 LLM API

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息

        Returns:
            LLM 响应 (字典)

        Raises:
            Exception: API 调用失败
        """
        import httpx

        url = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,  # 低温度以获得更稳定的输出
            "response_format": {"type": "json_object"},
        }

        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    result = response.json()

                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content)

            except httpx.TimeoutException as e:
                last_error = f"LLM API timeout after {self.timeout}s"
                logger.warning(f"{last_error}, retry {retry_count}/{self.max_retries}")
                retry_count += 1

            except httpx.HTTPStatusError as e:
                last_error = f"LLM API HTTP error: {e.response.status_code}"
                logger.warning(f"{last_error}, retry {retry_count}/{self.max_retries}")
                retry_count += 1

            except json.JSONDecodeError as e:
                last_error = f"LLM response JSON decode error: {e}"
                logger.warning(f"{last_error}, retry {retry_count}/{self.max_retries}")
                retry_count += 1

            except Exception as e:
                last_error = f"LLM API unexpected error: {e}"
                logger.error(last_error)
                retry_count += 1

            if retry_count <= self.max_retries:
                await asyncio.sleep(0.5 * retry_count)  # 指数退避

        raise Exception(f"LLM API failed after {self.max_retries + 1} attempts: {last_error}")


# ==================== NLU 服务 ====================


class NLUService:
    """
    NLU 服务

    处理自然语言职位需求解析。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        """
        初始化 NLU 服务

        Args:
            llm_client: LLM 客户端
        """
        self.llm = llm_client
        self._system_prompt: Optional[str] = None

    def _load_system_prompt(self) -> str:
        """
        加载系统提示词

        Returns:
            系统提示词文本
        """
        if self._system_prompt is None:
            try:
                with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                    self._system_prompt = f.read()
            except FileNotFoundError:
                logger.warning(f"System prompt not found at {SYSTEM_PROMPT_PATH}")
                self._system_prompt = "You are an HR assistant. Parse job requirements into JSON."
        return self._system_prompt

    async def parse(
        self,
        text: str,
        use_cache: bool = True,
    ) -> NLUParseResponse:
        """
        解析自然语言职位需求

        Args:
            text: 自然语言输入
            use_cache: 是否使用缓存

        Returns:
            NLUParseResponse

        Raises:
            ValueError: 输入为空
            Exception: 解析失败
        """
        if not text or not text.strip():
            raise ValueError("输入文本不能为空")

        text = text.strip()
        cache_key = self.llm._generate_cache_key(text)

        # 检查缓存
        if use_cache:
            cache = await get_cache()
            cached = await cache.get(cache_key)
            if cached:
                logger.info(f"Cache hit for NLU parse: {cache_key[:20]}...")
                try:
                    cached_data = json.loads(cached)
                    return NLUParseResponse(**cached_data)
                except Exception as e:
                    logger.warning(f"Failed to parse cached data: {e}")

        # 调用 LLM
        logger.info(f"Calling LLM for NLU parse: {text[:50]}...")
        system_prompt = self._load_system_prompt()

        result = await self.llm.call_llm(
            system_prompt=system_prompt,
            user_message=text,
        )

        # 规范化薪资
        if "job_requirement_draft" in result:
            draft = result["job_requirement_draft"]
            if "salary_min" in draft:
                draft["salary_min"] = self.llm._normalize_salary(draft.get("salary_min"))
            if "salary_max" in draft:
                draft["salary_max"] = self.llm._normalize_salary(draft.get("salary_max"))

        # 构建响应
        response = NLUParseResponse(**result)

        # 缓存结果
        if use_cache:
            cache = await get_cache()
            try:
                await cache.set(cache_key, response.model_dump_json())
                logger.info(f"Cached NLU result: {cache_key[:20]}...")
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

        return response

    async def parse_with_retry(
        self,
        text: str,
        max_retries: int = 3,
    ) -> NLUParseResponse:
        """
        带重试的解析

        Args:
            text: 自然语言输入
            max_retries: 最大重试次数

        Returns:
            NLUParseResponse
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self.parse(text, use_cache=(attempt == 0))
            except Exception as e:
                last_error = e
                logger.warning(f"NLU parse attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))

        raise Exception(f"NLU parse failed after {max_retries} attempts: {last_error}")


# ==================== 工厂函数 ====================


def create_llm_client() -> LLMClient:
    """
    创建 LLM 客户端

    Returns:
        LLMClient 实例
    """
    api_key = os.getenv("LLM_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("LLM_API_KEY not set, using placeholder")
        api_key = "placeholder"

    return LLMClient(
        api_key=api_key,
        model=os.getenv("LLM_MODEL", LLM_MODEL),
        api_base=os.getenv("LLM_API_BASE", os.getenv("LLM_BASE_URL", LLM_API_BASE)),
        timeout=float(os.getenv("LLM_TIMEOUT", str(LLM_TIMEOUT))),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", str(LLM_MAX_RETRIES))),
    )


def create_nlu_service() -> NLUService:
    """
    创建 NLU 服务

    Returns:
        NLUService 实例
    """
    return NLUService(llm_client=create_llm_client())


# ==================== 导出 ====================
__all__ = [
    "NLUService",
    "NLUParseResponse",
    "JobRequirementDraft",
    "ConfidenceScores",
    "ClarificationQuestion",
    "RedisCache",
    "LLMClient",
    "get_cache",
    "close_cache",
    "create_llm_client",
    "create_nlu_service",
]
