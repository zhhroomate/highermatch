#!/usr/bin/env python3
"""
HigherMatch™ Qdrant Collection Initialization Script
=====================================================

TruthBase™ 候选人向量数据库初始化脚本。

功能:
1. 创建 candidates Collection
2. 配置索引和优化器
3. 验证 Collection 配置

运行方式:
    python init_qdrant.py

环境变量:
    QDRANT_URL: Qdrant 服务地址 (默认 http://localhost:6333)
    QDRANT_API_KEY: Qdrant API Key (可选)
    EMBEDDING_DIMENSIONS: 向量维度 (默认 1536)

版本: 1.0.0
"""

import argparse
import asyncio
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 配置 ====================
class InitConfig(BaseModel):
    """初始化配置"""
    qdrant_url: str = Field(default="http://localhost:6333")
    api_key: str = Field(default="")
    timeout: int = Field(default=30)
    collection_name: str = Field(default="candidates")
    vector_size: int = Field(default=1536)
    distance: str = Field(default="Cosine")  # Cosine | Euclid | Dot
    seed_test_candidates: bool = Field(default=False)
    test_candidate_count: int = Field(default=3)


# ==================== Collection Schema ====================
# Qdrant 支持的 Payload 字段类型
# - keyword: 字符串精确匹配
# - integer: 整数范围查询
# - float: 浮点数范围查询
# - geo: 地理位置 (暂不使用)
# - text: 全文搜索 (暂不使用)

PAYLOAD_SCHEMA = {
    "candidate_id": {"type": "keyword"},
    "name": {"type": "keyword"},
    "city": {"type": "keyword"},
    "job_search_status": {"type": "keyword"},
    "skills": {"type": "keyword"},
    "preferred_job_titles": {"type": "keyword"},
    "preferred_locations": {"type": "keyword"},
    "total_years_exp": {"type": "integer"},
    "salary_min": {"type": "integer"},
    "salary_max": {"type": "integer"},
    "education_level": {"type": "keyword"},
    "created_at": {"type": "keyword"},
    "updated_at": {"type": "keyword"},
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


TEST_CANDIDATES = [
    {
        "candidate_id": "11111111-1111-4111-8111-111111111111",
        "name": "Li Ming",
        "city": "Chengdu",
        "job_search_status": "active",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
        "preferred_job_titles": ["Python Backend Engineer", "Backend Developer"],
        "preferred_locations": ["Chengdu", "Remote"],
        "total_years_exp": 5,
        "salary_min": 28000,
        "salary_max": 36000,
        "education_level": "bachelor",
        "summary": "Backend engineer focused on Python services, APIs, and data pipelines.",
    },
    {
        "candidate_id": "22222222-2222-4222-8222-222222222222",
        "name": "Wang Fang",
        "city": "Shanghai",
        "job_search_status": "passive",
        "skills": ["Java", "Spring Boot", "MySQL", "Kafka"],
        "preferred_job_titles": ["Java Backend Engineer", "Platform Engineer"],
        "preferred_locations": ["Shanghai"],
        "total_years_exp": 7,
        "salary_min": 35000,
        "salary_max": 45000,
        "education_level": "master",
        "summary": "Senior backend engineer with strong distributed systems and messaging experience.",
    },
    {
        "candidate_id": "33333333-3333-4333-8333-333333333333",
        "name": "Zhang Wei",
        "city": "Shenzhen",
        "job_search_status": "urgent",
        "skills": ["React", "TypeScript", "Node.js", "GraphQL"],
        "preferred_job_titles": ["Frontend Engineer", "Fullstack Engineer"],
        "preferred_locations": ["Shenzhen", "Guangzhou"],
        "total_years_exp": 4,
        "salary_min": 25000,
        "salary_max": 32000,
        "education_level": "bachelor",
        "summary": "Frontend engineer experienced in React applications and collaboration with product teams.",
    },
]


def _build_seed_text(candidate: dict) -> str:
    parts = [
        candidate.get("candidate_id", ""),
        candidate.get("name", ""),
        candidate.get("city", ""),
        ",".join(candidate.get("preferred_job_titles", [])),
        ",".join(candidate.get("skills", [])),
        ",".join(candidate.get("preferred_locations", [])),
        str(candidate.get("total_years_exp", "")),
        candidate.get("job_search_status", ""),
        candidate.get("summary", ""),
    ]
    return " | ".join(part for part in parts if part)


def _build_test_vector(seed_text: str, size: int) -> list[float]:
    values: list[float] = []
    counter = 0

    while len(values) < size:
        digest = hashlib.sha256(f"{seed_text}:{counter}".encode("utf-8")).digest()
        for byte in digest:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) == size:
                break
        counter += 1

    norm = sum(value * value for value in values) ** 0.5
    if norm == 0:
        return [0.0] * size

    return [round(value / norm, 8) for value in values]


# ==================== 初始化器 ====================
class QdrantInitializer:
    """Qdrant Collection 初始化器"""

    def __init__(self, config: InitConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["api-key"] = self.config.api_key

            self._client = httpx.AsyncClient(
                base_url=self.config.qdrant_url,
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()

    async def health_check(self) -> bool:
        """
        检查 Qdrant 健康状态

        Returns:
            True: 服务正常
        """
        try:
            for path in ("/readyz", "/collections", "/"):
                response = await self.client.get(path)
                if response.is_success:
                    try:
                        health = response.json()
                    except ValueError:
                        health = response.text
                    logger.info(f"Qdrant health via {path}: {health}")
                    return True
            logger.error("Qdrant health check failed: no healthy endpoint responded")
            return False
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def collection_exists(self, name: str) -> bool:
        """检查 Collection 是否存在"""
        try:
            response = await self.client.get(f"/collections/{name}")
            response.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise
        return False

    async def get_collection_info(self, name: str) -> Optional[dict]:
        """获取 Collection 信息"""
        try:
            response = await self.client.get(f"/collections/{name}")
            response.raise_for_status()
            return response.json().get("result")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def create_collection(self, name: str) -> bool:
        """
        创建 Collection

        Args:
            name: Collection 名称

        Returns:
            True: 创建成功

        Raises:
            Exception: 创建失败
        """
        # 检查是否已存在
        if await self.collection_exists(name):
            logger.info(f"Collection '{name}' already exists")
            return True

        # 构建创建请求
        create_params = {
            "vectors": {
                "size": self.config.vector_size,
                "distance": self.config.distance,
            },
            "params": {
                "hnsw_config": {
                    "m": 16,  # HNSW M 参数
                    "ef_construct": 200,  # HNSW 构造时的 ef 参数
                },
                "quantization_config": {
                    "scalar": {
                        "type": "int8",
                        "quantile": 0.99,
                        "always_ram": True,
                    }
                }
            },
            "hnsw_config": {
                "m": 16,
                "ef_construct": 200,
                "full_scan_threshold": 10000,
            },
            "optimizer_config": {
                "default_segment_number": 3,
                "indexing_threshold": 20000,
                "memmap_threshold": 50000,
                "vector_quantity": 1000,
            },
        }

        # 添加 payload schema
        if PAYLOAD_SCHEMA:
            create_params["payload_schema"] = PAYLOAD_SCHEMA

        # 发送创建请求
        logger.info(f"Creating collection '{name}' with params: {create_params}")

        response = await self.client.put(
            f"/collections/{name}",
            json=create_params
        )
        response.raise_for_status()

        result = response.json()
        logger.info(f"Collection creation response: {result}")

        # 等待 Collection 就绪
        await self._wait_for_collection(name)

        logger.info(f"Collection '{name}' created successfully")
        return True

    async def _wait_for_collection(self, name: str, timeout: int = 30) -> bool:
        """等待 Collection 就绪"""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                info = await self.get_collection_info(name)
                if info and info.get("status") == "green":
                    return True
            except Exception:
                pass

            await asyncio.sleep(0.5)

        logger.warning(f"Collection '{name}' may not be ready yet")
        return False

    async def delete_collection(self, name: str) -> bool:
        """
        删除 Collection

        Args:
            name: Collection 名称

        Returns:
            True: 删除成功
        """
        if not await self.collection_exists(name):
            logger.info(f"Collection '{name}' does not exist")
            return True

        response = await self.client.delete(f"/collections/{name}")
        response.raise_for_status()

        logger.info(f"Collection '{name}' deleted")
        return True

    async def recreate_collection(self, name: str) -> bool:
        """
        重建 Collection (删除后创建)

        Args:
            name: Collection 名称

        Returns:
            True: 重建成功
        """
        await self.delete_collection(name)
        await asyncio.sleep(1)  # 等待删除完成
        return await self.create_collection(name)

    async def get_collection_stats(self, name: str) -> Optional[dict]:
        """获取 Collection 统计信息"""
        info = await self.get_collection_info(name)
        if not info:
            return None

        return {
            "name": name,
            "vectors_count": info.get("vectors_count", 0),
            "points_count": info.get("points_count", 0),
            "status": info.get("status"),
            "indexed_vectors_count": info.get("indexed_vectors_count", 0),
        }

    async def upsert_points(self, name: str, points: list[dict]) -> int:
        """Upsert points into a collection."""
        response = await self.client.put(
            f"/collections/{name}/points",
            params={"wait": "true"},
            json={"points": points},
        )
        response.raise_for_status()
        logger.info("Upsert response: %s", response.json())
        return len(points)

    async def list_points(self, name: str, limit: int = 10) -> list[dict]:
        """Fetch a small sample of points from a collection."""
        response = await self.client.post(
            f"/collections/{name}/points/scroll",
            json={
                "limit": limit,
                "with_payload": True,
                "with_vector": False,
            },
        )
        response.raise_for_status()
        return response.json().get("result", {}).get("points", [])

    async def seed_test_candidates(self, name: str, count: int) -> list[dict]:
        """Seed deterministic test candidates into the collection."""
        seeded_at = _utc_now_iso()
        points: list[dict] = []
        seeded_candidates: list[dict] = []

        for candidate in TEST_CANDIDATES[:count]:
            payload = {
                "candidate_id": candidate["candidate_id"],
                "name": candidate["name"],
                "city": candidate["city"],
                "job_search_status": candidate["job_search_status"],
                "skills": candidate["skills"],
                "preferred_job_titles": candidate["preferred_job_titles"],
                "preferred_locations": candidate["preferred_locations"],
                "total_years_exp": candidate["total_years_exp"],
                "salary_min": candidate["salary_min"],
                "salary_max": candidate["salary_max"],
                "education_level": candidate["education_level"],
                "created_at": seeded_at,
                "updated_at": seeded_at,
                "summary": candidate["summary"],
            }
            points.append(
                {
                    "id": candidate["candidate_id"],
                    "vector": _build_test_vector(
                        _build_seed_text(candidate),
                        self.config.vector_size,
                    ),
                    "payload": payload,
                }
            )
            seeded_candidates.append(payload)

        await self.upsert_points(name, points)
        return seeded_candidates


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Initialize Qdrant and seed test candidates.")
    parser.add_argument(
        "--action",
        choices=["create", "recreate", "delete", "info"],
        default=os.getenv("INIT_ACTION", "create"),
        help="Collection action to execute.",
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant base URL.",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("QDRANT_COLLECTION", "candidates"),
        help="Collection name.",
    )
    parser.add_argument(
        "--vector-size",
        type=int,
        default=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
        help="Vector size for the collection.",
    )
    parser.add_argument(
        "--seed-test-candidates",
        action="store_true",
        default=os.getenv("SEED_TEST_CANDIDATES", "").lower() in {"1", "true", "yes"},
        help="After initialization, write three deterministic test candidate vectors.",
    )
    parser.add_argument(
        "--test-candidate-count",
        type=int,
        default=int(os.getenv("TEST_CANDIDATE_COUNT", "3")),
        help="Number of built-in test candidates to seed. Max is 3.",
    )
    return parser.parse_args()


# ==================== 主函数 ====================
async def main():
    """主函数"""
    args = parse_args()

    # 加载配置
    config = InitConfig(
        qdrant_url=args.qdrant_url,
        api_key=os.getenv("QDRANT_API_KEY", ""),
        collection_name=args.collection,
        vector_size=args.vector_size,
        seed_test_candidates=args.seed_test_candidates,
        test_candidate_count=max(1, min(args.test_candidate_count, len(TEST_CANDIDATES))),
    )

    logger.info("=" * 60)
    logger.info("HigherMatch™ Qdrant Collection Initialization")
    logger.info("=" * 60)
    logger.info(f"Qdrant URL: {config.qdrant_url}")
    logger.info(f"Collection: {config.collection_name}")
    logger.info(f"Vector Size: {config.vector_size}")
    logger.info(f"Distance: {config.distance}")
    logger.info(f"Seed test candidates: {config.seed_test_candidates}")
    logger.info("=" * 60)

    initializer = QdrantInitializer(config)

    try:
        # 1. 健康检查
        logger.info("\n[1/5] Checking Qdrant health...")
        if not await initializer.health_check():
            logger.error("Qdrant is not available")
            sys.exit(1)
        logger.info("Qdrant is healthy")

        # 2. 检查现有 Collection
        logger.info(f"\n[2/5] Checking collection '{config.collection_name}'...")
        exists = await initializer.collection_exists(config.collection_name)
        if exists:
            logger.info(f"Collection '{config.collection_name}' exists")
        else:
            logger.info(f"Collection '{config.collection_name}' does not exist")

        # 3. 获取命令行参数
        action = args.action

        if action == "recreate":
            # 重建 Collection
            logger.info(f"\n[3/5] Recreating collection...")
            await initializer.recreate_collection(config.collection_name)

        elif action == "delete":
            # 删除 Collection
            logger.info(f"\n[3/5] Deleting collection...")
            await initializer.delete_collection(config.collection_name)

        elif action == "info":
            # 查看信息
            logger.info(f"\n[3/5] Getting collection info...")
            stats = await initializer.get_collection_stats(config.collection_name)
            if stats:
                logger.info(f"Collection stats: {stats}")
            else:
                logger.info("Collection not found")

        else:
            # 创建 Collection (默认)
            logger.info(f"\n[3/5] Creating collection...")
            if exists:
                logger.info("Collection already exists, skipping creation")
            else:
                await initializer.create_collection(config.collection_name)

        if action != "delete":
            # 4. 验证配置
            logger.info(f"\n[4/6] Verifying collection config...")
            info = await initializer.get_collection_info(config.collection_name)
            if info:
                logger.info(f"Collection verified: {info.get('status')}")
                vectors_config = info.get("config", {}).get("params", {}).get("vectors", {})
                logger.info(f"  - Vector size: {vectors_config.get('size')}")
                logger.info(f"  - Distance: {vectors_config.get('distance')}")
            else:
                logger.warning("Could not verify collection config")

            # 5. 写入测试候选人
            if config.seed_test_candidates:
                logger.info(
                    f"\n[5/6] Seeding {config.test_candidate_count} test candidate vectors..."
                )
                seeded_candidates = await initializer.seed_test_candidates(
                    config.collection_name,
                    config.test_candidate_count,
                )
                for candidate in seeded_candidates:
                    logger.info(
                        "  - %s | %s | %s | skills=%s",
                        candidate["candidate_id"],
                        candidate["name"],
                        candidate["city"],
                        ", ".join(candidate["skills"]),
                    )

                sample_points = await initializer.list_points(
                    config.collection_name,
                    limit=config.test_candidate_count,
                )
                logger.info("Seed verification points: %s", len(sample_points))
                for point in sample_points:
                    payload = point.get("payload", {})
                    logger.info(
                        "    -> %s | %s | %s",
                        payload.get("candidate_id", point.get("id")),
                        payload.get("name"),
                        payload.get("preferred_job_titles"),
                    )
            else:
                logger.info("\n[5/6] Skipping test candidate seed")

            # 6. 显示统计信息
            logger.info(f"\n[6/6] Collection statistics...")
            stats = await initializer.get_collection_stats(config.collection_name)
            if stats:
                logger.info(f"  - Points count: {stats.get('points_count', 0)}")
                logger.info(f"  - Vectors count: {stats.get('vectors_count', 0)}")
                logger.info(f"  - Status: {stats.get('status')}")
            else:
                logger.info("No statistics available")
        else:
            logger.info("\n[4/4] Delete action completed; verification skipped")

        logger.info("\n" + "=" * 60)
        logger.info("Initialization completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)

    finally:
        await initializer.close()


# ==================== 入口 ====================
if __name__ == "__main__":
    asyncio.run(main())
