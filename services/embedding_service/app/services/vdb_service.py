"""
HigherMatch™ Embedding Service - Vector Database Service
========================================================

Qdrant 向量数据库操作模块 (TruthBase™)。

功能:
1. 管理 Qdrant Collection (创建、配置)
2. 候选人向量写入 (upsert)
3. 向量相似度检索 (ANN Search)

Collection 配置:
- vector_size: 1536
- distance: Cosine

版本: 1.0.0
"""

import logging
import os
from typing import Optional, Any
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 配置 ====================
class QdrantConfig(BaseModel):
    """Qdrant 配置"""
    url: str = Field(default="http://localhost:6333", description="Qdrant 服务 URL")
    api_key: str = Field(default="", description="Qdrant API Key (可选)")
    timeout: int = Field(default=30, description="超时时间(秒)")
    collection_name: str = Field(default="candidates", description="Collection 名称")
    vector_size: int = Field(default=1536, description="向量维度")
    distance: str = Field(default="Cosine", description="距离度量: Cosine | Euclid | Dot")


# ==================== 搜索过滤器模型 ====================
@dataclass
class SearchFilters:
    """搜索过滤器"""
    location: Optional[list[str]] = None      # 工作地点列表
    salary_min: Optional[int] = None          # 最低薪资 (分/月)
    salary_max: Optional[int] = None          # 最高薪资 (分/月)
    job_status: Optional[list[str]] = None    # 求职状态列表
    skills: Optional[list[str]] = None        # 技能列表 (至少匹配一个)


# ==================== 搜索结果模型 ====================
@dataclass
class CandidateSearchResult:
    """候选人搜索结果"""
    candidate_id: str
    score: float
    payload: dict


# ==================== Qdrant API 客户端 ====================
class QdrantClient:
    """
    Qdrant REST API 客户端

    支持 Collection 管理和向量操作。
    """

    def __init__(self, config: Optional[QdrantConfig] = None):
        """
        初始化 Qdrant 客户端

        Args:
            config: Qdrant 配置
        """
        if config is None:
            config = QdrantConfig(
                url=os.getenv("QDRANT_URL", "http://localhost:6333"),
                api_key=os.getenv("QDRANT_API_KEY", ""),
                timeout=int(os.getenv("QDRANT_TIMEOUT", "30")),
                collection_name=os.getenv("QDRANT_COLLECTION", "candidates"),
                vector_size=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
                distance=os.getenv("QDRANT_DISTANCE", "Cosine"),
            )
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端 (懒加载)"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["api-key"] = self.config.api_key

            self._client = httpx.AsyncClient(
                base_url=self.config.url,
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[dict] = None,
    ) -> dict:
        """
        发送 API 请求

        Args:
            method: HTTP 方法
            path: API 路径
            json_data: 请求数据

        Returns:
            响应 JSON

        Raises:
            QdrantError: 请求失败时抛出
        """
        try:
            response = await self.client.request(
                method=method,
                url=path,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Qdrant request timeout: {e}")
            raise QdrantError("Qdrant 请求超时")
        except httpx.HTTPStatusError as e:
            logger.error(f"Qdrant HTTP error: {e.response.status_code} - {e.response.text}")
            raise QdrantError(f"Qdrant 请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Qdrant request failed: {e}")
            raise QdrantError(f"Qdrant 请求失败: {str(e)}")


# ==================== Collection 管理 ====================
class CollectionManager:
    """Collection 管理器"""

    def __init__(self, client: QdrantClient):
        self.client = client

    async def create_collection(
        self,
        name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: str = "Cosine",
    ) -> bool:
        """
        创建 Collection

        Args:
            name: Collection 名称
            vector_size: 向量维度
            distance: 距离度量 (Cosine | Euclid | Dot)

        Returns:
            True: 创建成功

        Raises:
            QdrantError: 创建失败
        """
        name = name or self.client.config.collection_name
        vector_size = vector_size or self.client.config.vector_size

        # 检查是否已存在
        try:
            await self.get_collection(name)
            logger.info(f"Collection '{name}' already exists")
            return True
        except QdrantError:
            pass

        # 创建 Collection
        await self.client._request(
            "PUT",
            f"/collections/{name}",
            json_data={
                "vectors": {
                    "size": vector_size,
                    "distance": distance,
                },
                "optimizers_config": {
                    "default_segment_number": 3,
                    "indexing_threshold": 20000,
                },
            }
        )

        logger.info(f"Collection '{name}' created (size={vector_size}, distance={distance})")
        return True

    async def get_collection(self, name: Optional[str] = None) -> dict:
        """
        获取 Collection 信息

        Args:
            name: Collection 名称

        Returns:
            Collection 信息字典
        """
        name = name or self.client.config.collection_name
        result = await self.client._request("GET", f"/collections/{name}")
        return result

    async def delete_collection(self, name: Optional[str] = None) -> bool:
        """
        删除 Collection

        Args:
            name: Collection 名称

        Returns:
            True: 删除成功
        """
        name = name or self.client.config.collection_name
        await self.client._request("DELETE", f"/collections/{name}")
        logger.info(f"Collection '{name}' deleted")
        return True

    async def list_collections(self) -> list[str]:
        """
        列出所有 Collection

        Returns:
            Collection 名称列表
        """
        result = await self.client._request("GET", "/collections")
        return [c["name"] for c in result.get("collections", [])]

    async def collection_exists(self, name: Optional[str] = None) -> bool:
        """检查 Collection 是否存在"""
        name = name or self.client.config.collection_name
        try:
            await self.get_collection(name)
            return True
        except QdrantError:
            return False


# ==================== 向量操作 ====================
class VectorOperations:
    """向量操作"""

    def __init__(self, client: QdrantClient):
        self.client = client

    async def upsert_points(
        self,
        points: list[dict],
        collection: Optional[str] = None,
    ) -> int:
        """
        批量插入/更新向量点

        Args:
            points: 点列表，每个点包含:
                - id: 点 ID (str)
                - vector: 向量 (list[float])
                - payload: 元数据 (dict)
            collection: Collection 名称

        Returns:
            插入的点数

        Raises:
            QdrantError: 操作失败
        """
        collection = collection or self.client.config.collection_name

        # 构建 points 格式
        formatted_points = []
        for point in points:
            formatted_points.append({
                "id": str(point["id"]),
                "vector": point["vector"],
                "payload": point.get("payload", {}),
            })

        result = await self.client._request(
            "PUT",
            f"/collections/{collection}/points",
            json_data={"points": formatted_points}
        )

        count = len(formatted_points)
        logger.info(f"Upserted {count} points to '{collection}'")
        return count

    async def delete_points(
        self,
        ids: list[str],
        collection: Optional[str] = None,
    ) -> bool:
        """
        删除向量点

        Args:
            ids: 点 ID 列表
            collection: Collection 名称

        Returns:
            True: 删除成功
        """
        collection = collection or self.client.config.collection_name

        await self.client._request(
            "POST",
            f"/collections/{collection}/points/delete",
            json_data={"points": ids}
        )

        logger.info(f"Deleted {len(ids)} points from '{collection}'")
        return True

    async def retrieve_point(
        self,
        point_id: str,
        collection: Optional[str] = None,
    ) -> Optional[dict]:
        """
        获取单个向量点

        Args:
            point_id: 点 ID
            collection: Collection 名称

        Returns:
            点数据或 None
        """
        collection = collection or self.client.config.collection_name

        result = await self.client._request(
            "GET",
            f"/collections/{collection}/points/{point_id}"
        )

        return result.get("result")

    async def search(
        self,
        vector: list[float],
        collection: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        score_threshold: Optional[float] = None,
        with_payload: bool = True,
        filter_config: Optional[dict] = None,
    ) -> list[dict]:
        """
        向量相似度搜索 (ANN)

        Args:
            vector: 查询向量
            collection: Collection 名称
            limit: 返回数量
            offset: 偏移量
            score_threshold: 最低分数阈值
            with_payload: 是否返回 payload
            filter_config: 过滤条件

        Returns:
            搜索结果列表

        Raises:
            QdrantError: 搜索失败
        """
        collection = collection or self.client.config.collection_name

        # 构建请求
        search_params = {
            "limit": limit,
            "offset": offset,
            "with_payload": with_payload,
        }

        if score_threshold is not None:
            search_params["score_threshold"] = score_threshold

        if filter_config:
            search_params["filter"] = filter_config

        result = await self.client._request(
            "POST",
            f"/collections/{collection}/points/search",
            json_data={
                "vector": vector,
                **search_params
            }
        )

        return result.get("result", [])


# ==================== 候选人 VDB 服务 ====================
async def upsert_candidate_to_vdb(
    candidate_id: str,
    vector: list[float],
    payload: dict,
    collection: Optional[str] = None,
) -> bool:
    """
    将候选人向量写入 Qdrant

    Args:
        candidate_id: 候选人 ID (UUID 字符串)
        vector: 1536 维 Embedding 向量
        payload: 候选人元数据，包含:
            - job_search_status: 求职状态
            - city: 当前城市
            - salary_min: 期望最低薪资 (分/月)
            - salary_max: 期望最高薪资 (分/月)
            - skills: 技能列表
            - total_years_exp: 总工作年限
            - name: 姓名
            - preferred_job_titles: 期望职位
        collection: Collection 名称 (默认 candidates)

    Returns:
        True: 写入成功

    Raises:
        QdrantError: 写入失败

    Example:
        >>> payload = {
        ...     "job_search_status": "active",
        ...     "city": "Beijing",
        ...     "salary_min": 3000000,
        ...     "salary_max": 5000000,
        ...     "skills": ["Python", "FastAPI"],
        ...     "total_years_exp": 5,
        ...     "name": "张三",
        ... }
        >>> await upsert_candidate_to_vdb("uuid-xxx", [0.1] * 1536, payload)
        True
    """
    client = get_qdrant_client()
    ops = VectorOperations(client)

    point = {
        "id": str(candidate_id),
        "vector": vector,
        "payload": {
            "candidate_id": str(candidate_id),
            **payload
        }
    }

    await ops.upsert_points([point], collection=collection)

    logger.info(f"Upserted candidate {candidate_id} to VDB (vector_dim={len(vector)})")
    return True


async def delete_candidate_from_vdb(
    candidate_id: str,
    collection: Optional[str] = None,
) -> bool:
    """
    从 Qdrant 删除候选人向量

    Args:
        candidate_id: 候选人 ID
        collection: Collection 名称

    Returns:
        True: 删除成功
    """
    client = get_qdrant_client()
    ops = VectorOperations(client)

    await ops.delete_points([str(candidate_id)], collection=collection)

    logger.info(f"Deleted candidate {candidate_id} from VDB")
    return True


async def search_candidates(
    query_vector: list[float],
    filters: Optional[SearchFilters] = None,
    top_k: int = 200,
    collection: Optional[str] = None,
) -> list[CandidateSearchResult]:
    """
    执行候选人 ANN 检索

    在 Qdrant candidates collection 中执行向量相似度搜索，
    支持按 location、salary 等条件过滤。

    Args:
        query_vector: 查询向量 (1536 维)
        filters: 搜索过滤器，包含:
            - location: 工作地点列表 (OR 匹配)
            - salary_min: 最低薪资 (分/月)
            - salary_max: 最高薪资 (分/月)
            - job_status: 求职状态列表
            - skills: 技能列表 (至少匹配一个)
        top_k: 返回数量上限 (默认 200)
        collection: Collection 名称 (默认 candidates)

    Returns:
        有序的搜索结果列表，按 score 降序排列

    Raises:
        QdrantError: 搜索失败

    Example:
        >>> filters = SearchFilters(
        ...     location=["Beijing", "Shanghai"],
        ...     salary_min=3000000,
        ...     job_status=["active", "passive"]
        ... )
        >>> results = await search_candidates([0.1] * 1536, filters, top_k=50)
        >>> for r in results:
        ...     print(f"{r.candidate_id}: {r.score:.4f}")
    """
    client = get_qdrant_client()
    ops = VectorOperations(client)

    # 构建过滤条件
    filter_config = _build_filter_config(filters)

    # 执行搜索
    points = await ops.search(
        vector=query_vector,
        collection=collection,
        limit=top_k,
        with_payload=True,
    )

    # 转换为结果对象
    results = []
    for point in points:
        results.append(CandidateSearchResult(
            candidate_id=point["payload"].get("candidate_id", point["id"]),
            score=point.get("score", 0.0),
            payload=point.get("payload", {}),
        ))

    logger.info(
        f"Search completed: {len(results)} results "
        f"(filters={filter_config is not None})"
    )

    return results


def _build_filter_config(filters: Optional[SearchFilters]) -> Optional[dict]:
    """
    构建 Qdrant 过滤条件

    Args:
        filters: 搜索过滤器

    Returns:
        Qdrant filter 配置字典
    """
    if filters is None:
        return None

    conditions = []

    # 地点过滤 (city 字段)
    if filters.location:
        location_conditions = [
            {"key": "city", "match": {"value": loc}}
            for loc in filters.location
        ]
        if location_conditions:
            conditions.append({"should": location_conditions})

    # 薪资过滤
    if filters.salary_min is not None:
        conditions.append({
            "key": "salary_min",
            "range": {"gte": filters.salary_min}
        })

    if filters.salary_max is not None:
        conditions.append({
            "key": "salary_max",
            "range": {"lte": filters.salary_max}
        })

    # 求职状态过滤
    if filters.job_status:
        status_conditions = [
            {"key": "job_search_status", "match": {"value": status}}
            for status in filters.job_status
        ]
        if status_conditions:
            conditions.append({"should": status_conditions})

    # 技能过滤 (至少匹配一个)
    if filters.skills:
        skill_conditions = [
            {"key": "skills", "match": {"value": skill}}
            for skill in filters.skills
        ]
        if skill_conditions:
            conditions.append({"should": skill_conditions})

    if not conditions:
        return None

    return {"must": conditions} if len(conditions) > 1 else conditions[0]


async def get_candidate_from_vdb(
    candidate_id: str,
    collection: Optional[str] = None,
) -> Optional[dict]:
    """
    获取候选人的 VDB 记录

    Args:
        candidate_id: 候选人 ID
        collection: Collection 名称

    Returns:
        候选人数据或 None
    """
    client = get_qdrant_client()
    ops = VectorOperations(client)

    point = await ops.retrieve_point(str(candidate_id), collection=collection)
    return point


# ==================== 单例 ====================
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 客户端实例"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient()
    return _qdrant_client


async def close_qdrant_client() -> None:
    """关闭 Qdrant 客户端"""
    global _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None


# ==================== 错误类 ====================
class QdrantError(Exception):
    """Qdrant 相关错误"""
    pass


# ==================== 导出 ====================
__all__ = [
    "QdrantClient",
    "QdrantConfig",
    "QdrantError",
    "SearchFilters",
    "CandidateSearchResult",
    "CollectionManager",
    "VectorOperations",
    "upsert_candidate_to_vdb",
    "delete_candidate_from_vdb",
    "search_candidates",
    "get_candidate_from_vdb",
    "get_qdrant_client",
    "close_qdrant_client",
]
