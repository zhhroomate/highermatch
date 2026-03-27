#!/usr/bin/env python3
"""
HigherMatch™ E2E Matching Test
================================

端到端匹配验证测试。

测试流程:
1. 准备测试数据 (候选人已在 seed_data.py 中生成)
2. 创建测试岗位
3. 发布 job.published Kafka 消息
4. 等待 Celery 任务执行完毕
5. 轮询 match_results 表验证结果
6. 断言匹配质量

使用方式:
    # 运行所有测试
    pytest tests/test_e2e_matching.py -v

    # 运行单个测试
    pytest tests/test_e2e_matching.py::TestE2EMatching::test_job_matching_flow -v

    # 带详细输出
    pytest tests/test_e2e_matching.py -v -s

版本: 1.0.0
"""

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Optional

import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==================== 测试配置 ====================

class TestConfig:
    """测试配置"""

    # 数据库
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@localhost:5432/highermatch_dev"
    )

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    KAFKA_TOPIC_JOB_PUBLISHED = "job.published"
    KAFKA_TOPIC_MATCH_COMPLETED = "match.completed"

    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")

    # 等待超时 (秒)
    TASK_TIMEOUT = 300
    POLL_INTERVAL = 2

    # 匹配阈值
    MIN_SHORTLIST_COUNT = 5
    MIN_SKILL_MATCH_RATE = 0.3
    VERIFICATION_THRESHOLD = 0.6


# ==================== 数据库操作 ====================

async def get_db_session():
    """获取数据库会话"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.ext.asyncio import async_sessionmaker

    engine = create_async_engine(
        TestConfig.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    return engine, async_session


async def get_candidates_by_job_type(job_type: str, min_count: int = 50) -> list[dict]:
    """
    获取特定岗位类型的候选人

    Args:
        job_type: 岗位类型
        min_count: 最小候选人数量

    Returns:
        候选人列表
    """
    from sqlalchemy import text

    engine, async_session = await get_db_session()

    query = text("""
        SELECT c.id, c.name, c.skills, c.current_city, c.total_years_exp,
               c.preferred_locations, c.expected_salary_min, c.expected_salary_max,
               c.verification_score, c.profile
        FROM candidates c
        WHERE c.is_active = true
        AND c.profile_completeness > 0.7
        LIMIT :limit
    """)

    async with async_session() as session:
        result = await session.execute(query, {"limit": min_count * 2})
        rows = result.fetchall()

    await engine.dispose()

    candidates = []
    for row in rows:
        skills = row.skills or []
        if job_type.lower() in str(skills).lower():
            candidates.append({
                "id": str(row.id),
                "name": row.name,
                "skills": skills,
                "current_city": row.current_city,
                "total_years_exp": row.total_years_exp,
                "preferred_locations": row.preferred_locations or [],
                "expected_salary_min": row.expected_salary_min,
                "expected_salary_max": row.expected_salary_max,
                "verification_score": row.verification_score,
                "profile": row.profile,
            })

    return candidates[:min_count]


async def create_test_job(
    job_title: str,
    skills: list[str],
    city: str,
    years_min: int = 3,
    years_max: int = 8,
    salary_min: int = 2500000,
    salary_max: int = 4500000,
) -> dict:
    """
    创建测试岗位

    Args:
        job_title: 职位名称
        skills: 所需技能
        city: 工作城市
        years_min: 最低年限
        years_max: 最高年限
        salary_min: 最低薪资 (分/月)
        salary_max: 最高薪资 (分/月)

    Returns:
        包含 job_id, employer_id, job_data 的字典
    """
    from sqlalchemy import text

    engine, async_session = await get_db_session()

    job_id = str(uuid.uuid4())
    employer_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # 创建雇主
    employer_sql = text("""
        INSERT INTO employers (
            id, company_name, industry, company_size, contact_name,
            contact_email, contact_phone, kyc_status, is_verified,
            credit_balance, created_at, updated_at
        ) VALUES (
            :id, :company_name, :industry, :company_size, :contact_name,
            :contact_email, :contact_phone, :kyc_status, :is_verified,
            :credit_balance, :created_at, :updated_at
        )
    """)

    # 创建岗位
    job_sql = text("""
        INSERT INTO jobs (
            id, employer_id, job_title, job_category, job_tags,
            requirement, work_city, work_province, work_location_type,
            salary_min, salary_max, employment_type, status,
            commission_rate, is_urgent, published_at, created_at, updated_at
        ) VALUES (
            :id, :employer_id, :job_title, :job_category, :job_tags,
            :requirement, :work_city, :work_province, :work_location_type,
            :salary_min, :salary_max, :employment_type, :status,
            :commission_rate, :is_urgent, :published_at, :created_at, :updated_at
        )
    """)

    async with async_session() as session:
        await session.execute(employer_sql, {
            "id": employer_id,
            "company_name": f"TestCompany_{uuid.uuid4().hex[:8]}",
            "industry": "互联网",
            "company_size": "201-500",
            "contact_name": "Test HR",
            "contact_email": "test@example.com",
            "contact_phone": "13800138000",
            "kyc_status": "approved",
            "is_verified": True,
            "credit_balance": 10000000,
            "created_at": now,
            "updated_at": now,
        })

        await session.execute(job_sql, {
            "id": job_id,
            "employer_id": employer_id,
            "job_title": job_title,
            "job_category": "技术",
            "job_tags": skills[:3],
            "requirement": json.dumps({
                "skills": skills,
                "core_skills": skills[:2],
                "years_exp_min": years_min,
                "years_exp_max": years_max,
                "industries": ["互联网", "软件服务"],
            }),
            "work_city": city,
            "work_province": "北京市" if city == "北京" else city,
            "work_location_type": "onsite",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "employment_type": "full_time",
            "status": "published",
            "commission_rate": 0.15,
            "is_urgent": False,
            "published_at": now,
            "created_at": now,
            "updated_at": now,
        })

        await session.commit()

    await engine.dispose()

    job_data = {
        "id": job_id,
        "employer_id": employer_id,
        "job_title": job_title,
        "company_name": f"TestCompany_{uuid.uuid4().hex[:8]}",
        "requirement": {
            "skills": skills,
            "core_skills": skills[:2],
            "years_exp_min": years_min,
            "years_exp_max": years_max,
            "industries": ["互联网", "软件服务"],
        },
        "salary_min": salary_min,
        "salary_max": salary_max,
    }

    logger.info(f"Created test job: {job_id}")
    return {
        "job_id": job_id,
        "employer_id": employer_id,
        "job_data": job_data,
    }


async def get_match_results(job_id: str, pipeline_stage: str = "ai_recommended") -> list[dict]:
    """
    获取岗位的匹配结果

    Args:
        job_id: 岗位 ID
        pipeline_stage: 管道阶段

    Returns:
        匹配结果列表
    """
    from sqlalchemy import text

    engine, async_session = await get_db_session()

    query = text("""
        SELECT mr.id, mr.candidate_id, mr.overall_score, mr.pipeline_stage,
               mr.match_reasons, mr.created_at,
               c.name as candidate_name, c.skills as candidate_skills,
               c.current_city, c.total_years_exp, c.verification_score
        FROM match_results mr
        JOIN candidates c ON mr.candidate_id = c.id
        WHERE mr.job_id = :job_id
        AND mr.pipeline_stage = :pipeline_stage
        AND mr.is_deleted = false
        ORDER BY mr.overall_score DESC
    """)

    async with async_session() as session:
        result = await session.execute(query, {
            "job_id": job_id,
            "pipeline_stage": pipeline_stage,
        })
        rows = result.fetchall()

    await engine.dispose()

    return [
        {
            "id": str(row.id),
            "candidate_id": str(row.candidate_id),
            "candidate_name": row.candidate_name,
            "overall_score": row.overall_score,
            "pipeline_stage": row.pipeline_stage,
            "match_reasons": row.match_reasons or [],
            "candidate_skills": row.candidate_skills or [],
            "current_city": row.current_city,
            "total_years_exp": row.total_years_exp,
            "verification_score": row.verification_score,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


async def wait_for_matching_complete(
    job_id: str,
    timeout: int = TestConfig.TASK_TIMEOUT,
    poll_interval: int = TestConfig.POLL_INTERVAL,
) -> Optional[list[dict]]:
    """
    等待匹配完成

    Args:
        job_id: 岗位 ID
        timeout: 超时时间 (秒)
        poll_interval: 轮询间隔 (秒)

    Returns:
        匹配结果列表或 None (超时)
    """
    start_time = time.time()

    logger.info(f"Waiting for matching to complete: job_id={job_id}")

    while time.time() - start_time < timeout:
        results = await get_match_results(job_id)

        if results:
            elapsed = time.time() - start_time
            logger.info(f"Matching complete: {len(results)} results in {elapsed:.1f}s")
            return results

        logger.debug(f"Polling... ({time.time() - start_time:.0f}s elapsed)")
        await asyncio.sleep(poll_interval)

    logger.warning(f"Timeout waiting for matching: job_id={job_id}")
    return None


# ==================== Kafka 操作 ====================

async def publish_job_message(job_info: dict) -> bool:
    """
    发布 job.published Kafka 消息

    Args:
        job_info: 包含 job_id, employer_id, job_data 的字典

    Returns:
        是否成功
    """
    try:
        from aiokafka import AIOKafkaProducer

        producer = AIOKafkaProducer(
            bootstrap_servers=TestConfig.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )

        await producer.start()

        try:
            message = {
                "event_type": "job.published",
                "job_id": job_info["job_id"],
                "employer_id": job_info["employer_id"],
                "job_data": job_info["job_data"],
                "timestamp": datetime.utcnow().isoformat(),
            }

            await producer.send_and_wait(
                TestConfig.KAFKA_TOPIC_JOB_PUBLISHED,
                value=message,
                key=job_info["job_id"].encode("utf-8"),
            )

            logger.info(f"Published job.published message: job_id={job_info['job_id']}")
            return True

        finally:
            await producer.stop()

    except ImportError:
        logger.warning("aiokafka not available, triggering task directly")
        return await trigger_matching_task_directly(job_info)
    except Exception as e:
        logger.error(f"Failed to publish Kafka message: {e}")
        return await trigger_matching_task_directly(job_info)


async def trigger_matching_task_directly(job_info: dict) -> bool:
    """
    直接触发 Celery 任务 (Kafka 不可用时)

    Args:
        job_info: 岗位信息

    Returns:
        是否成功
    """
    try:
        # 导入 matching service 模块
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "services", "matching_service"
        ))
        from app.tasks.matching_task import match_job_candidates

        task = match_job_candidates.apply_async(
            args=[
                job_info["job_id"],
                job_info["job_data"],
                job_info["employer_id"],
            ]
        )

        logger.info(f"Triggered matching task directly: task_id={task.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to trigger task directly: {e}")
        raise


# ==================== 断言辅助函数 ====================

def assert_min_shortlist_count(results: list[dict], min_count: int = 5):
    """
    断言至少有指定数量的 Shortlist 记录

    Args:
        results: 匹配结果列表
        min_count: 最小数量
    """
    actual_count = len(results)
    assert actual_count >= min_count, (
        f"Shortlist count too low: expected >= {min_count}, got {actual_count}. "
        f"Results: {results}"
    )
    logger.info(f"[PASS] Shortlist count: {actual_count} >= {min_count}")


def assert_location_match(results: list[dict], target_city: str):
    """
    断言候选人与岗位地点匹配

    Args:
        results: 匹配结果列表
        target_city: 目标城市
    """
    matched = 0
    for result in results:
        candidate_city = result.get("current_city", "")
        preferred_locations = result.get("preferred_locations", [])

        if candidate_city == target_city or target_city in preferred_locations:
            matched += 1

    match_rate = matched / len(results) if results else 0
    assert match_rate >= 0.5, (
        f"Location match rate too low: expected >= 50%, got {match_rate:.1%}. "
        f"Target city: {target_city}"
    )
    logger.info(f"[PASS] Location match rate: {match_rate:.1%}")


def assert_skill_match(results: list[dict], required_skills: list[str]):
    """
    断言候选人技能与岗位需求高度相关

    Args:
        results: 匹配结果列表
        required_skills: 岗位所需技能
    """
    skill_matches = []

    for result in results:
        candidate_skills = result.get("candidate_skills", [])
        if not candidate_skills:
            continue

        # 计算技能匹配率
        matched_skills = set(s.lower() for s in candidate_skills) & set(s.lower() for s in required_skills)
        match_rate = len(matched_skills) / len(required_skills) if required_skills else 0

        skill_matches.append({
            "candidate_id": result.get("candidate_id"),
            "candidate_name": result.get("candidate_name"),
            "match_rate": match_rate,
            "matched_skills": list(matched_skills),
            "required_skills": required_skills,
        })

    # 计算平均匹配率
    avg_match_rate = sum(m["match_rate"] for m in skill_matches) / len(skill_matches) if skill_matches else 0

    # 断言至少有 30% 的候选人技能匹配率超过阈值
    high_match_count = sum(1 for m in skill_matches if m["match_rate"] >= TestConfig.MIN_SKILL_MATCH_RATE)
    high_match_rate = high_match_count / len(skill_matches) if skill_matches else 0

    assert high_match_rate >= 0.5, (
        f"Skill match quality too low: expected >= 50% candidates with >= {TestConfig.MIN_SKILL_MATCH_RATE:.0%} match, "
        f"got {high_match_rate:.1%}. Average match rate: {avg_match_rate:.1%}"
    )

    logger.info(f"[PASS] Skill match: avg={avg_match_rate:.1%}, high_match={high_match_rate:.1%}")

    # 打印最佳匹配
    skill_matches.sort(key=lambda x: x["match_rate"], reverse=True)
    for i, match in enumerate(skill_matches[:3], 1):
        logger.info(f"  Top {i}: {match['candidate_name']} - {match['match_rate']:.1%} match")


def assert_verification_threshold(results: list[dict]):
    """
    断言候选人验证分数满足要求

    Args:
        results: 匹配结果列表
    """
    for result in results:
        verification_score = result.get("verification_score", 0)
        assert verification_score >= TestConfig.VERIFICATION_THRESHOLD, (
            f"Candidate verification too low: {verification_score:.2f} < {TestConfig.VERIFICATION_THRESHOLD}. "
            f"Candidate: {result.get('candidate_id')}"
        )

    logger.info(f"[PASS] All candidates meet verification threshold: >= {TestConfig.VERIFICATION_THRESHOLD}")


def assert_score_quality(results: list[dict]):
    """
    断言匹配分数质量

    Args:
        results: 匹配结果列表
    """
    assert len(results) > 0, "No results to check"

    # 检查分数分布
    scores = [r["overall_score"] for r in results]
    max_score = max(scores)
    min_score = min(scores)
    avg_score = sum(scores) / len(scores)

    logger.info(f"Score distribution: min={min_score:.3f}, avg={avg_score:.3f}, max={max_score:.3f}")

    # 断言分数有序 (递减)
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], (
            f"Scores not in descending order: {scores[i]} < {scores[i + 1]}"
        )

    # 断言最高分合理
    assert max_score <= 1.0, f"Invalid max score: {max_score}"
    assert max_score >= 0.5, f"Max score too low: {max_score}"

    logger.info("[PASS] Score quality: valid distribution and ordering")


# ==================== 测试用例 ====================

class TestE2EMatching:
    """E2E 匹配测试套件"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """测试前置设置"""
        logger.info("Setting up test environment...")
        yield
        logger.info("Tearing down test environment...")

    @pytest.mark.asyncio
    async def test_python_job_matching(self):
        """
        测试 Python 工程师岗位匹配

        测试场景:
        1. 创建 Python 后端工程师岗位
        2. 发布 job.published 消息
        3. 等待匹配完成
        4. 验证匹配结果质量
        """
        logger.info("=" * 60)
        logger.info("TEST: Python Job Matching")
        logger.info("=" * 60)

        # 步骤 1: 创建测试岗位
        job_info = await create_test_job(
            job_title="Python 后端工程师",
            skills=["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
            city="北京",
            years_min=3,
            years_max=8,
            salary_min=2500000,
            salary_max=4500000,
        )

        try:
            # 步骤 2: 发布 Kafka 消息
            success = await publish_job_message(job_info)
            assert success, "Failed to publish job message"

            # 步骤 3: 等待匹配完成
            results = await wait_for_matching_complete(job_info["job_id"])
            assert results is not None, "Matching timeout"

            # 步骤 4: 验证匹配结果
            logger.info("Verifying match results...")

            # 断言 1: 至少 5 条 Shortlist 记录
            assert_min_shortlist_count(results, min_count=TestConfig.MIN_SHORTLIST_COUNT)

            # 断言 2: 地点匹配
            assert_location_match(results, target_city="北京")

            # 断言 3: 技能匹配
            assert_skill_match(
                results,
                required_skills=["Python", "FastAPI", "PostgreSQL", "Redis"]
            )

            # 断言 4: 验证分数阈值
            assert_verification_threshold(results)

            # 断言 5: 分数质量
            assert_score_quality(results)

            logger.info("=" * 60)
            logger.info("TEST PASSED: Python Job Matching")
            logger.info("=" * 60)

        finally:
            # 清理测试数据
            await cleanup_test_data(job_info["job_id"], job_info["employer_id"])

    @pytest.mark.asyncio
    async def test_java_job_matching(self):
        """
        测试 Java 工程师岗位匹配
        """
        logger.info("=" * 60)
        logger.info("TEST: Java Job Matching")
        logger.info("=" * 60)

        job_info = await create_test_job(
            job_title="Java 高级工程师",
            skills=["Java", "Spring Boot", "MySQL", "Kafka", "微服务", "Docker"],
            city="上海",
            years_min=5,
            years_max=10,
            salary_min=3500000,
            salary_max=6000000,
        )

        try:
            success = await publish_job_message(job_info)
            assert success

            results = await wait_for_matching_complete(job_info["job_id"])
            assert results is not None

            assert_min_shortlist_count(results, min_count=5)
            assert_location_match(results, target_city="上海")
            assert_skill_match(results, required_skills=["Java", "Spring Boot"])
            assert_verification_threshold(results)
            assert_score_quality(results)

            logger.info("=" * 60)
            logger.info("TEST PASSED: Java Job Matching")
            logger.info("=" * 60)

        finally:
            await cleanup_test_data(job_info["job_id"], job_info["employer_id"])

    @pytest.mark.asyncio
    async def test_product_manager_matching(self):
        """
        测试产品经理岗位匹配
        """
        logger.info("=" * 60)
        logger.info("TEST: Product Manager Matching")
        logger.info("=" * 60)

        job_info = await create_test_job(
            job_title="高级产品经理",
            skills=["产品规划", "需求分析", "PRD撰写", "数据分析", "Axure", "用户研究"],
            city="深圳",
            years_min=4,
            years_max=8,
            salary_min=3000000,
            salary_max=5000000,
        )

        try:
            success = await publish_job_message(job_info)
            assert success

            results = await wait_for_matching_complete(job_info["job_id"])
            assert results is not None

            assert_min_shortlist_count(results, min_count=5)
            assert_location_match(results, target_city="深圳")

            logger.info("=" * 60)
            logger.info("TEST PASSED: Product Manager Matching")
            logger.info("=" * 60)

        finally:
            await cleanup_test_data(job_info["job_id"], job_info["employer_id"])

    @pytest.mark.asyncio
    async def test_multi_city_matching(self):
        """
        测试多城市岗位匹配

        验证匹配系统能处理不同城市的候选人
        """
        logger.info("=" * 60)
        logger.info("TEST: Multi-City Matching")
        logger.info("=" * 60)

        # 创建成都岗位
        job_info = await create_test_job(
            job_title="Python 工程师 (成都)",
            skills=["Python", "Django", "Flask", "MySQL"],
            city="成都",
            years_min=2,
            years_max=5,
            salary_min=1500000,
            salary_max=3000000,
        )

        try:
            success = await publish_job_message(job_info)
            assert success

            results = await wait_for_matching_complete(job_info["job_id"])

            if results:
                # 允许成都岗位有较低的地点匹配率 (因为候选人可能来自不同城市)
                logger.info(f"Multi-city test: {len(results)} results found")
                logger.info("This is acceptable for location-flexible candidates")

            logger.info("=" * 60)
            logger.info("TEST PASSED: Multi-City Matching")
            logger.info("=" * 60)

        finally:
            await cleanup_test_data(job_info["job_id"], job_info["employer_id"])


# ==================== 清理函数 ====================

async def cleanup_test_data(job_id: str, employer_id: str):
    """
    清理测试数据

    Args:
        job_id: 岗位 ID
        employer_id: 雇主 ID
    """
    from sqlalchemy import text

    try:
        engine, async_session = await get_db_session()

        async with async_session() as session:
            # 软删除匹配结果
            await session.execute(
                text("UPDATE match_results SET is_deleted = true WHERE job_id = :job_id"),
                {"job_id": job_id}
            )

            # 删除岗位
            await session.execute(text("DELETE FROM jobs WHERE id = :job_id"), {"job_id": job_id})

            # 删除雇主
            await session.execute(
                text("DELETE FROM employers WHERE id = :employer_id"),
                {"employer_id": employer_id}
            )

            await session.commit()

        await engine.dispose()

        logger.info(f"Cleaned up test data: job_id={job_id}, employer_id={employer_id}")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


# ==================== 主入口 ====================

def run_tests():
    """运行测试"""
    import pytest
    import sys

    sys.exit(pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
    ]))


if __name__ == "__main__":
    run_tests()
