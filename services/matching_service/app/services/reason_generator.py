"""
HigherMatch™ Matching Service - Reason Generator
=================================================

AI 匹配原因生成模块。

使用 LLM 生成个性化的匹配原因，提升推荐的说服力。

版本: 1.0.0
"""

import json
import logging
import os
import re
from typing import Optional

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 配置 ====================
class ReasonGeneratorConfig(BaseModel):
    """原因生成器配置"""
    api_key: str = Field(default="", description="API 密钥")
    base_url: str = Field(default="https://api.openai.com/v1", description="API URL")
    model: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=500, description="最大 token 数")
    timeout: int = Field(default=30, description="超时时间(秒)")


# ==================== 匹配原因模型 ====================
class MatchReason(BaseModel):
    """匹配原因"""
    overall: str = Field(description="整体推荐理由")
    highlights: list[str] = Field(default_factory=list, description="亮点列表")
    concerns: list[str] = Field(default_factory=list, description="潜在顾虑")
    suggestion: str = Field(description="面试建议")


class BatchReasonRequest(BaseModel):
    """批量生成请求"""
    job_data: dict
    candidates_data: list[dict]
    scores_data: list[dict]  # 评分结果


class BatchReasonResponse(BaseModel):
    """批量生成响应"""
    reasons: list[MatchReason]
    failed_count: int = 0


# ==================== System Prompt ====================
REASON_GENERATION_SYSTEM_PROMPT = """你是一个专业的招聘顾问 AI，负责为候选人与职位的匹配生成个性化推荐理由。

你的任务是：
1. 基于评分数据和候选人/职位信息，生成有说服力的推荐理由
2. 突出候选人的优势与职位的匹配度
3. 适度提及潜在顾虑，体现专业性
4. 提供面试建议，帮助面试官更好地评估候选人

输出要求：
- 语言专业、亲和
- 推荐理由要有说服力，但不要夸大
- 每条理由控制在合适长度

输出格式 (JSON):
{
    "overall": "整体推荐理由 (1-2 句话)",
    "highlights": ["亮点1", "亮点2", "亮点3"],
    "concerns": ["顾虑1"] 或 [],
    "suggestion": "面试建议 (1 句话)"
}
"""


# ==================== 原因生成器 ====================
class ReasonGenerator:
    """AI 匹配原因生成器"""

    def __init__(self, config: Optional[ReasonGeneratorConfig] = None):
        if config is None:
            config = ReasonGeneratorConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("LLM_MODEL", "gpt-4"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "500")),
                timeout=int(os.getenv("LLM_TIMEOUT", "30")),
            )
        self.config = config
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

    def _build_prompt(self, job_data: dict, candidate_data: dict, scores_data: dict) -> str:
        """
        构建生成提示词

        Args:
            job_data: 职位数据
            candidate_data: 候选人数据
            scores_data: 评分结果

        Returns:
            提示词字符串
        """
        # 职位信息摘要
        job_title = job_data.get("job_title", "未知职位")
        company_name = job_data.get("company_name", "未知公司")
        job_skills = ", ".join(job_data.get("skills", [])[:5])
        job_years = f"{job_data.get('years_exp_min', 0)}-{job_data.get('years_exp_max', 0)}年"

        # 候选人信息摘要
        candidate_name = candidate_data.get("name", "候选人")
        candidate_title = ""
        work_history = candidate_data.get("work_history", [])
        if work_history:
            latest = work_history[0]
            candidate_title = latest.get("title", "")
        candidate_skills = ", ".join(candidate_data.get("skills", [])[:5])
        candidate_years = candidate_data.get("total_years_exp", 0)

        # 评分摘要
        skill_score = scores_data.get("skill_score", 0)
        experience_score = scores_data.get("experience_score", 0)
        culture_score = scores_data.get("culture_score", 0)
        salary_score = scores_data.get("salary_score", 0)
        trajectory_score = scores_data.get("trajectory_score", 0)
        overall_score = scores_data.get("overall_score", 0)

        # 匹配的技能
        matched_skills = scores_data.get("skill_matched", [])
        unmatched_skills = scores_data.get("skill_unmatched", [])

        prompt = f"""请为以下候选人与职位的匹配生成推荐理由：

【职位信息】
- 职位: {job_title}
- 公司: {company_name}
- 所需技能: {job_skills}
- 经验要求: {job_years}

【候选人信息】
- 姓名: {candidate_name}
- 当前/最近职位: {candidate_title}
- 技能: {candidate_skills}
- 工作年限: {candidate_years}年

【匹配评分】
- 技能匹配: {skill_score:.0%}
- 经验匹配: {experience_score:.0%}
- 文化契合: {culture_score:.0%}
- 薪资匹配: {salary_score:.0%}
- 职业轨迹: {trajectory_score:.0%}
- 综合评分: {overall_score:.0%}

【技能匹配详情】
- 已匹配技能: {', '.join(matched_skills[:3]) if matched_skills else '无'}
- 未匹配技能: {', '.join(unmatched_skills[:2]) if unmatched_skills else '无'}

请生成专业、亲和的推荐理由。
"""
        return prompt

    async def generate_reason(
        self,
        job_data: dict,
        candidate_data: dict,
        scores_data: dict,
    ) -> Optional[MatchReason]:
        """
        生成单条匹配原因

        Args:
            job_data: 职位数据
            candidate_data: 候选人数据
            scores_data: 评分结果

        Returns:
            MatchReason 或 None (失败时)
        """
        try:
            prompt = self._build_prompt(job_data, candidate_data, scores_data)

            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": REASON_GENERATION_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                }
            )
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return MatchReason(
                    overall=data.get("overall", ""),
                    highlights=data.get("highlights", []),
                    concerns=data.get("concerns", []),
                    suggestion=data.get("suggestion", ""),
                )

            logger.warning(f"Failed to parse reason JSON: {content[:100]}")
            return None

        except Exception as e:
            logger.error(f"Reason generation failed: {e}")
            return None

    async def generate_batch_reasons(
        self,
        job_data: dict,
        candidates_data: list[dict],
        scores_data: list[dict],
    ) -> BatchReasonResponse:
        """
        批量生成匹配原因

        Args:
            job_data: 职位数据
            candidates_data: 候选人数据列表
            scores_data: 评分结果列表

        Returns:
            BatchReasonResponse
        """
        reasons = []
        failed_count = 0

        for i, (candidate, scores) in enumerate(zip(candidates_data, scores_data)):
            reason = await self.generate_reason(job_data, candidate, scores)
            if reason:
                reasons.append(reason)
            else:
                # 生成默认原因
                reasons.append(MatchReason(
                    overall=f"综合评分 {scores.get('overall_score', 0):.0%}",
                    highlights=[f"技能匹配 {scores.get('skill_score', 0):.0%}"],
                    concerns=[],
                    suggestion="建议安排面试深入了解",
                ))
                failed_count += 1

        return BatchReasonResponse(
            reasons=reasons,
            failed_count=failed_count,
        )

    def generate_simple_reason(
        self,
        job_data: dict,
        candidate_data: dict,
        scores_data: dict,
    ) -> str:
        """
        生成简单的文本推荐理由 (不使用 LLM)

        Args:
            job_data: 职位数据
            candidate_data: 候选人数据
            scores_data: 评分结果

        Returns:
            推荐理由文本
        """
        overall_score = scores_data.get("overall_score", 0)
        skill_score = scores_data.get("skill_score", 0)
        matched_skills = scores_data.get("skill_matched", [])

        parts = []

        # 整体评价
        if overall_score >= 0.8:
            parts.append("非常匹配")
        elif overall_score >= 0.6:
            parts.append("较匹配")
        else:
            parts.append("有一定匹配度")

        # 技能亮点
        if matched_skills and skill_score >= 0.6:
            parts.append(f"核心技能{matched_skills[0]}匹配度高")

        # 经验评价
        experience_score = scores_data.get("experience_score", 0)
        if experience_score >= 0.9:
            parts.append("工作经验与岗位要求高度吻合")

        return "，".join(parts) if parts else f"综合匹配度 {overall_score:.0%}"


# ==================== 单例 ====================
_reason_generator: Optional[ReasonGenerator] = None


def get_reason_generator() -> ReasonGenerator:
    """获取原因生成器实例"""
    global _reason_generator
    if _reason_generator is None:
        _reason_generator = ReasonGenerator()
    return _reason_generator


async def close_reason_generator() -> None:
    """关闭原因生成器"""
    global _reason_generator
    if _reason_generator is not None:
        await _reason_generator.close()
        _reason_generator = None


# ==================== 导出 ====================
__all__ = [
    "ReasonGeneratorConfig",
    "MatchReason",
    "BatchReasonRequest",
    "BatchReasonResponse",
    "ReasonGenerator",
    "get_reason_generator",
    "close_reason_generator",
]
