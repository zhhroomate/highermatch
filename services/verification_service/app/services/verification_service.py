"""
HigherMatch™ Verification Service - TruthBase Verification
========================================================

候选人交叉验证服务模块。

功能:
1. 消费 Kafka topic: candidate.updated
2. 多源验证:
   - 学历验证 (mock)
   - 技能一致性验证 (LLM)
3. 计算综合 verification_score
4. 更新 candidates 表
5. 标记 manual_override 需求

版本: 1.0.0
"""

import json
import logging
import os
import re
from typing import Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 验证配置 ====================
class VerificationConfig(BaseModel):
    """验证服务配置"""
    llm_api_key: str = Field(default="", description="LLM API 密钥")
    llm_base_url: str = Field(default="https://api.openai.com/v1", description="LLM API URL")
    llm_model: str = Field(default="gpt-4", description="LLM 模型")
    llm_timeout: int = Field(default=60, description="超时时间(秒)")
    kafka_bootstrap_servers: str = Field(default="localhost:9092", description="Kafka 地址")
    kafka_topic: str = Field(default="candidate.updated", description="监听 topic")
    kafka_consumer_group: str = Field(default="verification-service", description="消费者组")
    score_threshold: float = Field(default=0.3, description="人工复核阈值")


# ==================== 验证结果模型 ====================
@dataclass
class EducationVerificationResult:
    """学历验证结果"""
    is_verified: bool
    score: float  # 0.0 - 1.0
    verified_schools: list[str] = field(default_factory=list)
    failed_schools: list[str] = field(default_factory=list)
    details: str = ""


@dataclass
class SkillConsistencyResult:
    """技能一致性验证结果"""
    is_consistent: bool
    score: float  # 0.0 - 1.0
    matched_skills: list[str] = field(default_factory=list)
    unmatched_skills: list[str] = field(default_factory=list)
    analysis: str = ""


@dataclass
class VerificationResult:
    """综合验证结果"""
    candidate_id: str
    education_score: float
    skill_consistency_score: float
    verification_score: float
    requires_manual_override: bool
    is_verified: bool
    verified_at: datetime = field(default_factory=datetime.utcnow)
    details: dict = field(default_factory=dict)
    error: Optional[str] = None


# ==================== Mock 学历数据库 ====================
# 模拟的学历验证数据库
MOCK_EDUCATION_DB = {
    # 顶级院校
    "清华大学": {"level": "985", "rank": 1, "verified": True},
    "北京大学": {"level": "985", "rank": 2, "verified": True},
    "复旦大学": {"level": "985", "rank": 3, "verified": True},
    "上海交通大学": {"level": "985", "rank": 4, "verified": True},
    "浙江大学": {"level": "985", "rank": 5, "verified": True},
    "南京大学": {"level": "985", "rank": 6, "verified": True},
    "中国科学技术大学": {"level": "985", "rank": 7, "verified": True},
    "哈尔滨工业大学": {"level": "985", "rank": 8, "verified": True},
    "西安交通大学": {"level": "985", "rank": 9, "verified": True},
    "同济大学": {"level": "985", "rank": 10, "verified": True},
    "中国人民大学": {"level": "985", "rank": 11, "verified": True},
    "北京航空航天大学": {"level": "985", "rank": 12, "verified": True},
    "武汉大学": {"level": "985", "rank": 13, "verified": True},
    "华中科技大学": {"level": "985", "rank": 14, "verified": True},
    "中山大学": {"level": "985", "rank": 15, "verified": True},

    # 211 院校
    "北京理工大学": {"level": "211", "rank": 50, "verified": True},
    "南开大学": {"level": "211", "rank": 20, "verified": True},
    "天津大学": {"level": "211", "rank": 25, "verified": True},
    "东南大学": {"level": "211", "rank": 22, "verified": True},
    "厦门大学": {"level": "211", "rank": 23, "verified": True},
    "山东大学": {"level": "211", "rank": 30, "verified": True},
    "中南大学": {"level": "211", "rank": 28, "verified": True},
    "四川大学": {"level": "211", "rank": 18, "verified": True},
    "电子科技大学": {"level": "211", "rank": 35, "verified": True},
    "北京师范大学": {"level": "211", "rank": 16, "verified": True},

    # 普通院校
    "北京邮电大学": {"level": "普通一本", "rank": 100, "verified": True},
    "华东理工大学": {"level": "普通一本", "rank": 120, "verified": True},
    "南京航空航天大学": {"level": "普通一本", "rank": 110, "verified": True},
}


# ==================== 学历验证 ====================
async def verify_education_mock(education: list[dict]) -> EducationVerificationResult:
    """
    Mock 学历验证

    基于预定义的院校数据库进行验证。

    Args:
        education: 教育经历列表，每个包含:
            - school: 学校名称
            - degree: 学位
            - major: 专业

    Returns:
        EducationVerificationResult
    """
    if not education:
        return EducationVerificationResult(
            is_verified=False,
            score=0.0,
            details="无教育经历信息"
        )

    verified_schools = []
    failed_schools = []
    total_score = 0.0
    total_weight = 0.0

    for edu in education:
        school = edu.get("school", "").strip()
        if not school:
            continue

        # 模糊匹配学校名称
        matched_school = None
        for db_school, info in MOCK_EDUCATION_DB.items():
            if school in db_school or db_school in school:
                matched_school = db_school
                break

        if matched_school:
            verified_schools.append(matched_school)
            info = MOCK_EDUCATION_DB[matched_school]

            # 根据院校级别计算分数
            if info["level"] == "985":
                school_score = 1.0
            elif info["level"] == "211":
                school_score = 0.85
            else:
                school_score = 0.7

            # 学位加成
            degree = edu.get("degree", "").lower()
            if "博士" in degree:
                degree_factor = 1.2
            elif "硕士" in degree:
                degree_factor = 1.1
            else:
                degree_factor = 1.0

            weighted_score = min(1.0, school_score * degree_factor)
            total_score += weighted_score
            total_weight += 1.0

            logger.info(f"Verified school: {school} -> {matched_school} (score={weighted_score:.2f})")
        else:
            failed_schools.append(school)
            total_score += 0.3  # 未识别院校基础分
            total_weight += 1.0
            logger.warning(f"Failed to verify school: {school}")

    # 计算平均分数
    avg_score = total_score / total_weight if total_weight > 0 else 0.0

    return EducationVerificationResult(
        is_verified=len(failed_schools) == 0,
        score=avg_score,
        verified_schools=verified_schools,
        failed_schools=failed_schools,
        details=f"验证了 {len(verified_schools)} 所院校，{len(failed_schools)} 所未识别"
    )


# ==================== 技能一致性验证 ====================
class SkillVerifier:
    """技能一致性验证器"""

    def __init__(self, config: Optional[VerificationConfig] = None):
        self.config = config or VerificationConfig()
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.llm_base_url,
                headers={
                    "Authorization": f"Bearer {self.config.llm_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.config.llm_timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def verify_skill_consistency(
        self,
        skills: list[str],
        work_history: list[dict],
    ) -> SkillConsistencyResult:
        """
        验证技能与工作经历的一致性

        使用 LLM 分析候选人的工作经历描述，
        评估其声明的技能是否真实体现在工作经历中。

        Args:
            skills: 候选人声明的技能列表
            work_history: 工作经历列表，每个包含:
                - company: 公司名称
                - title: 职位名称
                - description: 工作描述

        Returns:
            SkillConsistencyResult
        """
        if not skills:
            return SkillConsistencyResult(
                is_consistent=False,
                score=0.5,
                analysis="无技能信息"
            )

        if not work_history:
            return SkillConsistencyResult(
                is_consistent=False,
                score=0.3,
                unmatched_skills=skills,
                analysis="无工作经历信息，无法验证技能一致性"
            )

        # 构建工作经历文本
        work_text_parts = []
        for i, work in enumerate(work_history[:3]):  # 只取最近3份工作
            title = work.get("title", "未知职位")
            company = work.get("company", "未知公司")
            desc = work.get("description", "")[:500]
            work_text_parts.append(f"[工作{i+1}] 职位: {title} @ {company}\n描述: {desc}")

        work_text = "\n\n".join(work_text_parts)

        # 构建提示词
        system_prompt = """你是一个技能验证专家。请分析候选人的工作经历，判断其声明的技能是否真实可信。

分析要求:
1. 检查技能是否在工作描述中有实际应用
2. 评估技能与职位的匹配度
3. 识别可能虚报的技能

输出格式 (JSON):
{
    "matched_skills": ["技能1", "技能2"],
    "unmatched_skills": ["技能3"],
    "analysis": "分析说明",
    "consistency_score": 0.0-1.0
}
"""

        user_prompt = f"""请验证以下技能的真实性:

声明技能: {', '.join(skills)}

工作经历:
{work_text}
"""

        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.config.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 1000,
                }
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            try:
                # 提取 JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                else:
                    analysis = json.loads(content)

                matched = analysis.get("matched_skills", [])
                unmatched = analysis.get("unmatched_skills", [])
                consistency_score = analysis.get("consistency_score", 0.5)
                analysis_text = analysis.get("analysis", "")

                return SkillConsistencyResult(
                    is_consistent=consistency_score >= 0.5,
                    score=consistency_score,
                    matched_skills=matched,
                    unmatched_skills=unmatched,
                    analysis=analysis_text
                )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return SkillConsistencyResult(
                    is_consistent=False,
                    score=0.5,
                    analysis=f"解析失败: {content[:200]}"
                )

        except Exception as e:
            logger.error(f"Skill verification failed: {e}")
            return SkillConsistencyResult(
                is_consistent=False,
                score=0.5,
                analysis=f"验证失败: {str(e)}"
            )


# ==================== 综合验证服务 ====================
class VerificationService:
    """
    候选人交叉验证服务

    负责:
    1. 执行多源验证
    2. 计算综合分数
    3. 标记人工复核需求
    """

    def __init__(self, config: Optional[VerificationConfig] = None):
        self.config = config or VerificationConfig()
        self._skill_verifier: Optional[SkillVerifier] = None

    @property
    def skill_verifier(self) -> SkillVerifier:
        if self._skill_verifier is None:
            self._skill_verifier = SkillVerifier(self.config)
        return self._skill_verifier

    async def close(self) -> None:
        if self._skill_verifier is not None:
            await self._skill_verifier.close()

    async def verify_candidate(
        self,
        candidate_id: str,
        candidate_data: dict,
    ) -> VerificationResult:
        """
        执行候选人综合验证

        Args:
            candidate_id: 候选人 ID
            candidate_data: 候选人数据，包含:
                - education: 教育经历列表
                - skills: 技能列表
                - work_history: 工作经历列表

        Returns:
            VerificationResult
        """
        logger.info(f"Starting verification for candidate: {candidate_id}")

        try:
            # 1. 学历验证
            education = candidate_data.get("education", [])
            edu_result = await verify_education_mock(education)
            education_score = edu_result.score

            logger.info(
                f"Education verification: score={education_score:.2f}, "
                f"verified={edu_result.is_verified}"
            )

            # 2. 技能一致性验证
            skills = candidate_data.get("skills", [])
            work_history = candidate_data.get("work_history", [])
            skill_result = await self.skill_verifier.verify_skill_consistency(
                skills=skills,
                work_history=work_history,
            )
            skill_consistency_score = skill_result.score

            logger.info(
                f"Skill consistency verification: score={skill_consistency_score:.2f}, "
                f"matched={skill_result.matched_skills}"
            )

            # 3. 综合分数计算
            # education_score * 0.4 + skill_consistency_score * 0.6
            verification_score = (
                education_score * 0.4 +
                skill_consistency_score * 0.6
            )

            # 4. 判断是否需要人工复核
            requires_override = verification_score < self.config.score_threshold

            # 5. 构建结果
            result = VerificationResult(
                candidate_id=candidate_id,
                education_score=education_score,
                skill_consistency_score=skill_consistency_score,
                verification_score=verification_score,
                requires_manual_override=requires_override,
                is_verified=not requires_override,
                details={
                    "education": {
                        "verified_schools": edu_result.verified_schools,
                        "failed_schools": edu_result.failed_schools,
                        "details": edu_result.details,
                    },
                    "skill_consistency": {
                        "matched_skills": skill_result.matched_skills,
                        "unmatched_skills": skill_result.unmatched_skills,
                        "analysis": skill_result.analysis,
                    },
                    "calculation": {
                        "formula": "education_score * 0.4 + skill_consistency_score * 0.6",
                        "education_weight": 0.4,
                        "skill_weight": 0.6,
                    }
                }
            )

            logger.info(
                f"Verification completed: candidate={candidate_id}, "
                f"score={verification_score:.3f}, override_required={requires_override}"
            )

            return result

        except Exception as e:
            logger.error(f"Verification failed for candidate {candidate_id}: {e}")
            return VerificationResult(
                candidate_id=candidate_id,
                education_score=0.0,
                skill_consistency_score=0.0,
                verification_score=0.0,
                requires_manual_override=True,
                is_verified=False,
                error=str(e)
            )


# ==================== Kafka 消费者 ====================
class VerificationKafkaConsumer:
    """验证服务 Kafka 消费者"""

    def __init__(
        self,
        service: VerificationService,
        config: Optional[VerificationConfig] = None,
    ):
        self.service = service
        self.config = config or VerificationConfig()
        self._consumer = None
        self._running = False

    async def start(self) -> None:
        """启动消费者"""
        # TODO: 实现实际的 Kafka 消费者
        # 使用 aiokafka 或 kafka-python
        logger.info(
            f"Starting Kafka consumer: topic={self.config.kafka_topic}, "
            f"group={self.config.kafka_consumer_group}"
        )

    async def stop(self) -> None:
        """停止消费者"""
        self._running = False
        logger.info("Kafka consumer stopped")

    async def process_message(self, message: dict) -> VerificationResult:
        """
        处理 Kafka 消息

        Args:
            message: Kafka 消息，包含:
                - candidate_id: 候选人 ID
                - updated_fields: 更新的字段列表
                - timestamp: 时间戳

        Returns:
            VerificationResult
        """
        candidate_id = message.get("candidate_id")
        if not candidate_id:
            raise ValueError("Message missing candidate_id")

        logger.info(f"Processing verification for candidate: {candidate_id}")

        # TODO: 从数据库获取候选人数据
        # 这里简化处理，直接使用消息中的数据
        candidate_data = message.get("candidate_data", {})

        return await self.service.verify_candidate(
            candidate_id=candidate_id,
            candidate_data=candidate_data,
        )


# ==================== 单例 ====================
_verification_service: Optional[VerificationService] = None


def get_verification_service() -> VerificationService:
    """获取验证服务实例"""
    global _verification_service
    if _verification_service is None:
        _verification_service = VerificationService()
    return _verification_service


async def close_verification_service() -> None:
    """关闭验证服务"""
    global _verification_service
    if _verification_service is not None:
        await _verification_service.close()
        _verification_service = None


# ==================== 导出 ====================
__all__ = [
    "VerificationConfig",
    "EducationVerificationResult",
    "SkillConsistencyResult",
    "VerificationResult",
    "verify_education_mock",
    "SkillVerifier",
    "VerificationService",
    "VerificationKafkaConsumer",
    "get_verification_service",
    "close_verification_service",
]
