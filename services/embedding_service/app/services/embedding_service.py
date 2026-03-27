"""
HigherMatch™ Embedding Service - Embedding Module
=================================================

候选人档案向量化模块。

功能:
1. 将候选人字段拼接为自然语言描述
2. 调用 OpenAI API 获取 1536 维 Embedding 向量
3. 支持缓存和批量处理

版本: 1.0.0
"""

import hashlib
import logging
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 配置 ====================
class EmbeddingConfig(BaseModel):
    """Embedding 配置"""
    api_key: str = Field(default="", description="OpenAI API 密钥")
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="API 基础 URL"
    )
    model: str = Field(default="text-embedding-ada-002", description="Embedding 模型")
    dimensions: int = Field(default=1536, description="向量维度")
    timeout: int = Field(default=30, description="超时时间(秒)")


# ==================== 请求/响应模型 ====================
class EmbeddingRequest(BaseModel):
    """Embedding 请求"""
    model: str
    input: str
    encoding_format: str = "float"


class EmbeddingData(BaseModel):
    """Embedding 数据"""
    object: str
    embedding: list[float]
    index: int


class EmbeddingResponse(BaseModel):
    """Embedding 响应"""
    object: str
    data: list[EmbeddingData]
    model: str
    usage: dict


# ==================== 候选人 Profile 拼接 ====================
def build_candidate_profile_text(candidate: dict) -> str:
    """
    将候选人字段拼接为自然语言描述

    拼接规则:
    - 职位标题 + 工作年限
    - 技能列表
    - 工作地点
    - 期望薪资范围
    - 求职状态
    - 教育背景 (可选)
    - 工作经历摘要 (可选)

    Args:
        candidate: 候选人数据字典

    Returns:
        拼接后的自然语言描述
    """
    parts = []

    # 基础信息
    job_titles = candidate.get("preferred_job_titles", [])
    if job_titles:
        parts.append(f"期望职位: {', '.join(job_titles[:5])}")

    total_years = candidate.get("total_years_exp", 0)
    if total_years:
        parts.append(f"{total_years}年工作经验")

    # 技能
    skills = candidate.get("skills", [])
    if skills:
        skill_text = ", ".join(skills[:20])  # 限制技能数量
        parts.append(f"技能: {skill_text}")

    # 工作地点
    locations = candidate.get("preferred_locations", []) or []
    current_city = candidate.get("current_city", "")
    if current_city:
        locations.insert(0, current_city)

    if locations:
        location_text = "/".join(locations[:3])
        parts.append(f"地点: {location_text}")

    # 期望薪资
    salary_min = candidate.get("expected_salary_min", 0)
    salary_max = candidate.get("expected_salary_max", 0)
    if salary_min or salary_max:
        # 转换为万/月
        salary_min_wan = salary_min // 10000 if salary_min else 0
        salary_max_wan = salary_max // 10000 if salary_max else 0

        if salary_min_wan and salary_max_wan:
            parts.append(f"期望薪资: {salary_min_wan}-{salary_max_wan}万/月")
        elif salary_min_wan:
            parts.append(f"期望薪资: {salary_min_wan}万/月以上")
        elif salary_max_wan:
            parts.append(f"期望薪资: {salary_max_wan}万/月以下")

    # 求职状态
    status = candidate.get("job_search_status", "")
    status_map = {
        "active": "积极求职中",
        "passive": "观望机会",
        "not_looking": "暂不求职",
        "urgent": "紧急求职"
    }
    if status:
        status_text = status_map.get(status, status)
        parts.append(f"求职状态: {status_text}")

    # 教育背景
    education = candidate.get("education", [])
    if education and len(education) > 0:
        latest_edu = education[0] if isinstance(education[0], dict) else {}
        school = latest_edu.get("school", "")
        degree = latest_edu.get("degree", "")
        major = latest_edu.get("major", "")
        if school:
            edu_parts = [school]
            if degree:
                edu_parts.append(degree)
            if major:
                edu_parts.append(major)
            parts.append("学历: " + " ".join(edu_parts))

    # 工作经历摘要
    work_history = candidate.get("work_history", [])
    if work_history and len(work_history) > 0:
        latest_work = work_history[0] if isinstance(work_history[0], dict) else {}
        company = latest_work.get("company", "")
        title = latest_work.get("title", "")
        if company or title:
            work_parts = []
            if company:
                work_parts.append(f"曾在{company}")
            if title:
                work_parts.append(f"担任{title}")
            parts.append(" ".join(work_parts))

    # 个人简介
    summary = candidate.get("summary", "")
    if summary:
        parts.append(f"简介: {summary[:200]}")

    return "。".join(parts)


# ==================== Embedding 客户端 ====================
class EmbeddingClient:
    """
    OpenAI Embedding API 客户端

    用于将文本转换为 1536 维向量。
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        初始化 Embedding 客户端

        Args:
            config: Embedding 配置
        """
        if config is None:
            config = EmbeddingConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
                dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
                timeout=int(os.getenv("EMBEDDING_TIMEOUT", "30")),
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

    async def embed_text(self, text: str) -> list[float]:
        """
        获取文本的 Embedding 向量

        Args:
            text: 输入文本

        Returns:
            1536 维向量

        Raises:
            EmbeddingError: 请求失败时抛出
        """
        if not text or not text.strip():
            raise EmbeddingError("输入文本不能为空")

        # 截断过长的文本 (模型最大输入 8191 tokens)
        if len(text) > 30000:
            text = text[:30000]
            logger.warning("Text truncated to 30000 characters")

        try:
            response = await self.client.post(
                "/embeddings",
                json={
                    "model": self.config.model,
                    "input": text,
                    "encoding_format": "float",
                }
            )
            response.raise_for_status()

            result = response.json()
            embedding = result["data"][0]["embedding"]

            # 验证维度
            if len(embedding) != self.config.dimensions:
                logger.warning(
                    f"Embedding dimension mismatch: expected {self.config.dimensions}, "
                    f"got {len(embedding)}"
                )

            return embedding

        except httpx.TimeoutException as e:
            logger.error(f"Embedding request timeout: {e}")
            raise EmbeddingError("Embedding 请求超时")
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding HTTP error: {e.response.status_code} - {e.response.text}")
            raise EmbeddingError(f"Embedding 请求失败: {e.response.status_code}")
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse embedding response: {e}")
            raise EmbeddingError("Embedding 响应解析失败")
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise EmbeddingError(f"Embedding 失败: {str(e)}")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批量获取 Embedding 向量

        Args:
            texts: 输入文本列表

        Returns:
            向量列表
        """
        results = []
        for text in texts:
            try:
                vector = await self.embed_text(text)
                results.append(vector)
            except EmbeddingError as e:
                logger.error(f"Failed to embed text: {e}")
                results.append([0.0] * self.config.dimensions)  # 返回零向量
        return results


# ==================== 错误类 ====================
class EmbeddingError(Exception):
    """Embedding 相关错误"""
    pass


# ==================== 核心函数 ====================
async def embed_candidate_profile(candidate: dict) -> list[float]:
    """
    将候选人档案转换为 Embedding 向量

    将候选人字典中的字段拼接为自然语言描述，
    调用 OpenAI Embedding API 获取 1536 维向量。

    Args:
        candidate: 候选人数据字典，包含:
            - preferred_job_titles: 期望职位列表
            - total_years_exp: 总工作年限
            - skills: 技能列表
            - preferred_locations: 期望地点列表
            - current_city: 当前城市
            - expected_salary_min/max: 期望薪资范围
            - job_search_status: 求职状态
            - education: 教育经历列表
            - work_history: 工作经历列表
            - summary: 个人简介

    Returns:
        1536 维 Embedding 向量 (list[float])

    Raises:
        EmbeddingError: 向量化失败时抛出

    Example:
        >>> candidate = {
        ...     "preferred_job_titles": ["Python Engineer", "Backend Developer"],
        ...     "total_years_exp": 5,
        ...     "skills": ["Python", "FastAPI", "PostgreSQL"],
        ...     "current_city": "Beijing",
        ...     "expected_salary_min": 3000000,
        ...     "expected_salary_max": 5000000,
        ... }
        >>> vector = await embed_candidate_profile(candidate)
        >>> len(vector)
        1536
    """
    # 1. 拼接自然语言描述
    profile_text = build_candidate_profile_text(candidate)

    if not profile_text or not profile_text.strip():
        raise EmbeddingError("候选人档案为空，无法生成 Embedding")

    # 2. 获取 Embedding 向量
    client = get_embedding_client()
    vector = await client.embed_text(profile_text)

    logger.info(
        f"Generated embedding for candidate "
        f"(text_length={len(profile_text)}, vector_dim={len(vector)})"
    )

    return vector


# ==================== 缓存支持 ====================
_cache_client: Optional["RedisClient"] = None
EMBEDDING_CACHE_TTL = 3600 * 24 * 7  # 7 天


async def embed_candidate_profile_with_cache(candidate: dict) -> list[float]:
    """
    带缓存的候选人档案 Embedding

    Args:
        candidate: 候选人数据字典

    Returns:
        1536 维 Embedding 向量
    """
    # 生成缓存键
    cache_key = _generate_cache_key(candidate)

    # 尝试从缓存获取
    if _cache_client:
        try:
            cached = await _cache_client.get(cache_key)
            if cached:
                import json
                vector = json.loads(cached)
                logger.debug(f"Embedding cache hit: {cache_key[:16]}...")
                return vector
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

    # 生成新的 Embedding
    vector = await embed_candidate_profile(candidate)

    # 存入缓存
    if _cache_client and vector:
        try:
            import json
            await _cache_client.setex(
                cache_key,
                EMBEDDING_CACHE_TTL,
                json.dumps(vector)
            )
            logger.debug(f"Embedding cached: {cache_key[:16]}...")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    return vector


def _generate_cache_key(candidate: dict) -> str:
    """生成缓存键"""
    # 使用关键字段生成哈希
    key_data = {
        "skills": sorted(candidate.get("skills", [])[:10]),
        "titles": sorted(candidate.get("preferred_job_titles", [])[:3]),
        "city": candidate.get("current_city", ""),
        "years": candidate.get("total_years_exp", 0),
    }
    key_str = str(sorted(key_data.items()))
    return f"embedding:candidate:{hashlib.sha256(key_str.encode()).hexdigest()[:32]}"


# ==================== 单例 ====================
_embedding_client: Optional[EmbeddingClient] = None


def get_embedding_client() -> EmbeddingClient:
    """获取 Embedding 客户端实例"""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


async def close_embedding_client() -> None:
    """关闭 Embedding 客户端"""
    global _embedding_client
    if _embedding_client is not None:
        await _embedding_client.close()
        _embedding_client = None


def set_cache_client(cache_client: "RedisClient") -> None:
    """设置缓存客户端"""
    global _cache_client
    _cache_client = cache_client


# ==================== 导出 ====================
__all__ = [
    "EmbeddingClient",
    "EmbeddingConfig",
    "EmbeddingError",
    "build_candidate_profile_text",
    "embed_candidate_profile",
    "embed_candidate_profile_with_cache",
    "get_embedding_client",
    "close_embedding_client",
    "set_cache_client",
]
