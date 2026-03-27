"""
HigherMatch™ Advisor Service - AI Career Advisor
================================================

AI 职业顾问服务模块。

功能:
1. 获取候选人画像数据
2. 组装 System Prompt 进行角色扮演
3. 调用 LLM 生成专业回复
4. 识别求职意向并检索匹配职位
5. 返回亲和专业的指导建议

版本: 1.0.0
"""

import json
import logging
import os
import re
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 配置 ====================
class AdvisorConfig(BaseModel):
    """顾问服务配置"""
    llm_api_key: str = Field(default="", description="LLM API 密钥")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API 基础 URL"
    )
    llm_model: str = Field(default="gpt-4", description="LLM 模型")
    llm_max_tokens: int = Field(default=2000, description="最大 token 数")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    llm_timeout: int = Field(default=60, description="超时时间(秒)")
    system_prompt_path: str = Field(
        default="/workspace/highermatch/services/advisor_service/prompts/advisor_system.txt",
        description="系统提示词文件路径"
    )


# ==================== 请求/响应模型 ====================
class AdvisorChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=5000)
    context_id: str = Field(default="", description="会话上下文 ID")


class ActionCard(BaseModel):
    """行动卡片"""
    job_id: str = Field(description="职位 ID")
    job_title: str = Field(description="职位名称")
    company_name: str = Field(description="公司名称")
    match_reason: str = Field(description="匹配原因")
    match_score: float = Field(description="匹配分数 0.0-1.0")
    salary_range: str = Field(default="", description="薪资范围")
    location: str = Field(default="", description="工作地点")
    urgency: str = Field(default="normal", description="紧急程度: hot | normal")


class AdvisorAnalysis(BaseModel):
    """分析结果"""
    strengths: list[str] = Field(default_factory=list, description="优势")
    improvements: list[str] = Field(default_factory=list, description="可改进点")
    market_position: str = Field(default="", description="市场定位")


class AdvisorData(BaseModel):
    """响应数据"""
    reply: str = Field(description="回复内容 (Markdown 格式)")
    action_cards: list[ActionCard] = Field(default_factory=list, description="行动卡片列表")
    analysis: Optional[AdvisorAnalysis] = Field(default=None, description="分析结果")
    intent_detected: bool = Field(default=False, description="是否检测到求职意向")
    action_type: Optional[str] = Field(default=None, description="行动类型")


class AdvisorChatResponse(BaseModel):
    """聊天响应"""
    success: bool = Field(description="是否成功")
    data: Optional[AdvisorData] = Field(default=None, description="响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")


# ==================== 求职意向检测 ====================
JOB_INTENT_KEYWORDS = [
    # 直接意向
    "换工作", "找工作", "看机会", "找工作",
    "投简历", "面试", "offer", "入职",
    "薪资", "待遇", "package", "薪酬",
    "职位", "岗位", "机会", "工作",
    "招聘", "求职", "跳槽", "辞职",
    "工资", "加薪", "晋升",

    # 英文
    "job", "work", "hire", "offer",
    "salary", "interview", "career",

    # 问询
    "有没有", "可以推荐", "适合我", "匹配",
    "申请", "投递", "报名",
]


def detect_job_intent(message: str) -> bool:
    """
    检测用户是否表达求职意向

    Args:
        message: 用户消息

    Returns:
        True: 检测到求职意向
    """
    message_lower = message.lower()

    # 检查关键词
    for keyword in JOB_INTENT_KEYWORDS:
        if keyword.lower() in message_lower:
            return True

    # 检查问询模式
    intent_patterns = [
        r"(有没有|有没有.*的).*(职位|岗位|机会|工作)",
        r"(帮我|给我).*(推荐|找|看看).*(职位|岗位|机会)",
        r"(适合|匹配).*(我|我的).*(职位|岗位)",
        r"(申请|投递|报名).*(职位|岗位)",
    ]

    for pattern in intent_patterns:
        if re.search(pattern, message):
            return True

    return False


# ==================== 候选人画像构建 ====================
def build_candidate_profile_text(candidate: dict) -> str:
    """
    将候选人字典转换为提示词格式的文本

    Args:
        candidate: 候选人数据字典

    Returns:
        格式化的候选人描述
    """
    lines = []

    # 基本信息
    name = candidate.get("name") or "候选人"
    lines.append(f"【基本信息】")
    lines.append(f"- 姓名: {name}")

    if candidate.get("current_city"):
        lines.append(f"- 当前城市: {candidate.get('current_city')}")

    if candidate.get("age"):
        lines.append(f"- 年龄: {candidate.get('age')}岁")

    # 求职状态
    status_map = {
        "active": "积极求职中",
        "passive": "观望机会",
        "not_looking": "暂不求职",
        "urgent": "紧急求职",
    }
    status = candidate.get("job_search_status", "")
    status_text = status_map.get(status, status)
    lines.append(f"【求职状态】")
    lines.append(f"- 状态: {status_text}")

    # 工作经历
    work_history = candidate.get("work_history", [])
    lines.append(f"【工作经历】")

    if work_history:
        latest = work_history[0] if isinstance(work_history[0], dict) else {}
        total_years = candidate.get("total_years_exp", 0)
        lines.append(f"- 总年限: {total_years}年")

        if latest.get("title"):
            lines.append(f"- 当前/最近职位: {latest.get('title')}")
        if latest.get("company"):
            lines.append(f"- 所在公司: {latest.get('company')}")
        if latest.get("description"):
            desc = latest.get("description", "")[:200]
            lines.append(f"- 工作描述: {desc}")
    else:
        lines.append(f"- 总年限: {candidate.get('total_years_exp', 0)}年")

    # 技能
    skills = candidate.get("skills", [])
    lines.append(f"【技能分析】")

    if skills:
        # 按熟练度分组 (假设前1/3为精通，后1/3为了解)
        n = len(skills)
        if n >= 3:
            proficient = skills[:n//3] if n >= 3 else skills[:1]
            familiar = skills[n//3:2*n//3] if n >= 3 else skills[1:2]
            basic = skills[2*n//3:] if n >= 3 else skills[2:]

            lines.append(f"- 核心技能: {', '.join(skills[:5])}")
            if proficient:
                lines.append(f"- 精通: {', '.join(proficient[:5])}")
            if familiar:
                lines.append(f"- 熟悉: {', '.join(familiar[:5])}")
        else:
            lines.append(f"- 技能: {', '.join(skills)}")
    else:
        lines.append(f"- 暂无技能信息")

    # 教育背景
    education = candidate.get("education", [])
    lines.append(f"【教育背景】")

    if education:
        latest = education[0] if isinstance(education[0], dict) else {}
        if latest.get("school"):
            lines.append(f"- 毕业院校: {latest.get('school')}")
        if latest.get("degree"):
            lines.append(f"- 学历: {latest.get('degree')}")
        if latest.get("major"):
            lines.append(f"- 专业: {latest.get('major')}")
    else:
        lines.append(f"- 暂无教育信息")

    # 期望条件
    lines.append(f"【期望条件】")

    preferred_titles = candidate.get("preferred_job_titles", [])
    if preferred_titles:
        titles = preferred_titles[:3]
        lines.append(f"- 期望职位: {', '.join(titles)}")

    preferred_locations = candidate.get("preferred_locations", [])
    if preferred_locations:
        lines.append(f"- 期望城市: {', '.join(preferred_locations[:3])}")

    salary_min = candidate.get("expected_salary_min")
    salary_max = candidate.get("expected_salary_max")
    if salary_min or salary_max:
        # 转换为 K
        min_k = f"{salary_min//1000}K" if salary_min else "面议"
        max_k = f"{salary_max//1000}K" if salary_max else "面议"
        lines.append(f"- 期望薪资: {min_k}-{max_k}/月")

    preferred_industries = candidate.get("preferred_industries", [])
    if preferred_industries:
        lines.append(f"- 期望行业: {', '.join(preferred_industries[:3])}")

    # 竞争力分析
    lines.append(f"【竞争力分析】")

    completeness = candidate.get("profile_completeness", 0)
    lines.append(f"- 简历完整度: {completeness*100:.0f}%")

    # 计算市场分位数 (模拟)
    market_percentile = _calculate_market_percentile(candidate)
    lines.append(f"- 市场竞争力: Top {market_percentile}%")

    # 简历状态
    lines.append(f"【简历状态】")
    resume_parsed = candidate.get("resume_parsed_at")
    if resume_parsed:
        lines.append(f"- 简历已解析")
    else:
        lines.append(f"- 简历待完善")

    return "\n".join(lines)


def _calculate_market_percentile(candidate: dict) -> int:
    """
    计算市场分位数 (模拟实现)

    实际应基于 VDB 检索结果计算

    Args:
        candidate: 候选人数据

    Returns:
        分位数 (1-100)
    """
    # 基础分数
    score = 50

    # 工作年限加分 (上限 5 年)
    years = candidate.get("total_years_exp", 0)
    if years >= 3:
        score += min(years - 2, 5) * 3

    # 技能数量加分 (上限 10 个)
    skills_count = len(candidate.get("skills", []))
    if skills_count >= 5:
        score += min(skills_count - 4, 6) * 2

    # 简历完整度加分
    completeness = candidate.get("profile_completeness", 0)
    score += completeness * 20

    # 薪资期望合理性 (中等期望得分更高)
    salary_min = candidate.get("expected_salary_min", 0)
    if 20000 <= salary_min <= 50000:  # 合理区间
        score += 5

    # 转换为分位数 (分数越高，分位数越低 = 排名越靠前)
    percentile = max(5, min(95, 100 - score))

    return percentile


# ==================== LLM 客户端 ====================
class LLMClient:
    """简化的 LLM 客户端"""

    def __init__(self, config: Optional[AdvisorConfig] = None):
        if config is None:
            config = AdvisorConfig(
                llm_api_key=os.getenv("OPENAI_API_KEY", ""),
                llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                llm_model=os.getenv("LLM_MODEL", "gpt-4"),
                llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
                llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                llm_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
            )
        self.config = config
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

    async def chat(self, messages: list[dict]) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表

        Returns:
            助手的回复文本
        """
        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.config.llm_model,
                    "messages": messages,
                    "temperature": self.config.llm_temperature,
                    "max_tokens": self.config.llm_max_tokens,
                }
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise AdvisorError(f"LLM 请求失败: {str(e)}")


# ==================== 错误类 ====================
class AdvisorError(Exception):
    """顾问服务错误"""
    pass


# ==================== 职业顾问服务 ====================
@dataclass
class AdvisorContext:
    """顾问会话上下文"""
    session_id: str
    candidate_id: str
    messages: list[dict]
    created_at: datetime


class CareerAdvisor:
    """
    AI 职业顾问

    负责：
    1. 管理会话上下文
    2. 构建提示词
    3. 调用 LLM
    4. 检索匹配职位
    """

    def __init__(self, config: Optional[AdvisorConfig] = None):
        self.config = config or AdvisorConfig()
        self._llm_client: Optional[LLMClient] = None
        self._system_prompt: Optional[str] = None
        self._contexts: dict[str, AdvisorContext] = {}

    @property
    def llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient(self.config)
        return self._llm_client

    async def close(self) -> None:
        if self._llm_client is not None:
            await self._llm_client.close()

    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        if self._system_prompt is None:
            try:
                with open(self.config.system_prompt_path, "r", encoding="utf-8") as f:
                    self._system_prompt = f.read()
            except FileNotFoundError:
                logger.warning(f"System prompt file not found: {self.config.system_prompt_path}")
                self._system_prompt = "你是 HigherMatch™ 智能职业顾问，提供专业的职业发展建议。"
        return self._system_prompt

    def _build_system_message(self, candidate_profile: str) -> str:
        """
        构建系统消息

        Args:
            candidate_profile: 候选人画像文本

        Returns:
            完整的系统消息
        """
        base_prompt = self._load_system_prompt()
        return f"{base_prompt}\n\n## 当前候选人信息\n\n{candidate_profile}"

    async def chat(
        self,
        message: str,
        candidate_profile: dict,
        context_id: str = "",
    ) -> AdvisorChatResponse:
        """
        处理聊天请求

        Args:
            message: 用户消息
            candidate_profile: 候选人画像数据
            context_id: 会话上下文 ID

        Returns:
            聊天响应
        """
        try:
            # 1. 检测求职意向
            intent_detected = detect_job_intent(message)

            # 2. 构建系统消息
            candidate_text = build_candidate_profile_text(candidate_profile)
            system_message = self._build_system_message(candidate_text)

            # 3. 获取/创建会话上下文
            session_id = context_id or "default"

            # 4. 构建消息历史
            messages = [
                {"role": "system", "content": system_message},
            ]

            # 添加历史消息 (最近 10 轮)
            if session_id in self._contexts:
                history = self._contexts[session_id].messages[-20:]
                messages.extend(history)

            # 添加当前用户消息
            messages.append({"role": "user", "content": message})

            # 5. 调用 LLM
            reply = await self.llm_client.chat(messages)

            # 6. 更新会话历史
            if session_id not in self._contexts:
                self._contexts[session_id] = AdvisorContext(
                    session_id=session_id,
                    candidate_id=str(candidate_profile.get("id", "")),
                    messages=[],
                    created_at=datetime.utcnow(),
                )

            self._contexts[session_id].messages.append({"role": "user", "content": message})
            self._contexts[session_id].messages.append({"role": "assistant", "content": reply})

            # 7. 如果检测到求职意向，检索匹配职位
            action_cards = []
            if intent_detected:
                action_cards = await self._search_matching_jobs(candidate_profile)

            # 8. 构建响应
            return AdvisorChatResponse(
                success=True,
                data=AdvisorData(
                    reply=reply,
                    action_cards=action_cards,
                    analysis=AdvisorAnalysis(
                        strengths=self._extract_strengths(candidate_profile),
                        improvements=self._extract_improvements(candidate_profile),
                        market_position=self._generate_market_position(candidate_profile),
                    ),
                    intent_detected=intent_detected,
                    action_type="job_search" if intent_detected else None,
                )
            )

        except Exception as e:
            logger.error(f"Advisor chat failed: {e}")
            return AdvisorChatResponse(
                success=False,
                error=str(e),
            )

    async def _search_matching_jobs(
        self,
        candidate_profile: dict,
        top_k: int = 3,
    ) -> list[ActionCard]:
        """
        检索匹配的职位

        Args:
            candidate_profile: 候选人画像
            top_k: 返回数量

        Returns:
            行动卡片列表
        """
        # TODO: 集成 VDB 检索服务
        # 目前返回模拟数据

        skills = candidate_profile.get("skills", [])
        preferred_locations = candidate_profile.get("preferred_locations", ["北京"])

        # 模拟检索结果
        mock_jobs = [
            {
                "job_id": "job-001",
                "job_title": "高级Python工程师",
                "company_name": "字节跳动",
                "match_reason": f"您的{skills[0] if skills else 'Python'}技能与该职位高度匹配",
                "match_score": 0.92,
                "salary_range": "45-70K",
                "location": preferred_locations[0],
                "urgency": "hot",
            },
            {
                "job_id": "job-002",
                "job_title": "技术负责人",
                "company_name": "美团",
                "match_reason": "5年经验符合该岗位要求，有带团队机会",
                "match_score": 0.88,
                "salary_range": "50-65K",
                "location": preferred_locations[0],
                "urgency": "normal",
            },
            {
                "job_id": "job-003",
                "job_title": "后端架构师",
                "company_name": "蚂蚁集团",
                "match_reason": "技术栈匹配，职级发展空间大",
                "match_score": 0.85,
                "salary_range": "60-80K",
                "location": preferred_locations[0] if len(preferred_locations) > 1 else "杭州",
                "urgency": "normal",
            },
        ]

        return [ActionCard(**job) for job in mock_jobs[:top_k]]

    def _extract_strengths(self, candidate: dict) -> list[str]:
        """提取候选人优势"""
        strengths = []

        total_years = candidate.get("total_years_exp", 0)
        if total_years >= 5:
            strengths.append(f"拥有{total_years}年的工作经验")
        elif total_years >= 3:
            strengths.append(f"{total_years}年经验，处于职业黄金发展期")

        skills = candidate.get("skills", [])
        if skills:
            strengths.append(f"掌握{skills[0]}等{len(skills)}项核心技能")

        completeness = candidate.get("profile_completeness", 0)
        if completeness >= 0.8:
            strengths.append("简历信息完善，竞争力突出")

        return strengths

    def _extract_improvements(self, candidate: dict) -> list[str]:
        """提取可改进点"""
        improvements = []

        skills_count = len(candidate.get("skills", []))
        if skills_count < 5:
            improvements.append("建议补充更多相关技能，提高岗位匹配度")

        completeness = candidate.get("profile_completeness", 0)
        if completeness < 0.7:
            improvements.append("完善简历信息，突出个人优势")

        work_history = candidate.get("work_history", [])
        if len(work_history) < 2:
            improvements.append("建议补充更多工作经历，展示职业成长轨迹")

        return improvements

    def _generate_market_position(self, candidate: dict) -> str:
        """生成市场定位描述"""
        percentile = _calculate_market_percentile(candidate)

        if percentile <= 15:
            return "市场上极具竞争力的候选人，可重点关注高端职位"
        elif percentile <= 30:
            return "竞争力较强，具备头部企业的求职资格"
        elif percentile <= 50:
            return "具备一定竞争力，需突出差异化优势"
        else:
            return "建议进一步提升技能和经验，增强市场竞争力"


# ==================== 单例 ====================
_advisor: Optional[CareerAdvisor] = None


def get_advisor() -> CareerAdvisor:
    """获取职业顾问实例"""
    global _advisor
    if _advisor is None:
        _advisor = CareerAdvisor()
    return _advisor


async def close_advisor() -> None:
    """关闭职业顾问"""
    global _advisor
    if _advisor is not None:
        await _advisor.close()
        _advisor = None


# ==================== 导出 ====================
__all__ = [
    "AdvisorConfig",
    "AdvisorChatRequest",
    "AdvisorChatResponse",
    "AdvisorData",
    "ActionCard",
    "AdvisorAnalysis",
    "CareerAdvisor",
    "detect_job_intent",
    "build_candidate_profile_text",
    "get_advisor",
    "close_advisor",
]
