"""
HigherMatch™ Matching Service - Multi-Dimensional Scoring
=========================================================

多维评分算法模块。

实现 5 个维度的评分函数:
1. score_skill_match: Jaccard 相似度，核心技能权重 x2
2. score_experience_match: 完全在范围内=1.0，不足则线性衰减
3. score_culture_fit: 同行业=1.0，相关行业=0.7，无关=0.3
4. score_salary_match: 按重叠比例计算
5. score_trajectory: 分析职业上升轨迹

综合分数公式:
overall = skill*0.35 + experience*0.25 + culture*0.15 + salary*0.15 + trajectory*0.10

版本: 1.0.0
"""

import logging
import re
from typing import Optional
from dataclasses import dataclass, field

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 行业关联映射 ====================
# 定义行业之间的关联度
INDUSTRY_RELATIONS = {
    # 互联网
    "互联网": ["电子商务", "软件服务", "游戏", "社交网络", "云计算", "大数据", "人工智能"],
    "电子商务": ["互联网", "零售", "物流", "支付"],
    "软件服务": ["互联网", "云计算", "企业服务", "SaaS"],
    "云计算": ["软件服务", "互联网", "数据中心", "企业服务"],
    "人工智能": ["互联网", "软件服务", "云计算", "大数据", "自动驾驶"],
    "大数据": ["云计算", "人工智能", "软件服务", "数据分析"],

    # 金融
    "金融": ["银行", "保险", "证券", "基金", "互联网金融", "区块链"],
    "银行": ["金融", "互联网金融", "科技"],
    "证券": ["金融", "互联网金融", "数据分析"],
    "互联网金融": ["金融", "互联网", "银行", "支付", "区块链"],

    # 制造业
    "制造业": ["汽车", "电子", "机械", "化工", "能源"],
    "汽车": ["制造业", "新能源", "智能驾驶", "互联网"],
    "电子": ["制造业", "半导体", "消费电子", "通信"],
    "新能源": ["制造业", "汽车", "能源", "环保"],
    "半导体": ["电子", "制造业", "集成电路", "芯片"],

    # 医疗健康
    "医疗健康": ["制药", "医疗器械", "生物科技", "医疗服务", "互联网医疗"],
    "制药": ["医疗健康", "生物科技", "化学"],
    "医疗器械": ["医疗健康", "电子", "制造业"],
    "互联网医疗": ["医疗健康", "互联网", "人工智能"],
}


def get_industry_relationship(industry1: str, industry2: str) -> float:
    """
    获取两个行业的关联度

    Args:
        industry1: 行业 1
        industry2: 行业 2

    Returns:
        关联度 (0.0 - 1.0)
    """
    if not industry1 or not industry2:
        return 0.5  # 未知情况给中等分数

    industry1 = industry1.strip()
    industry2 = industry2.strip()

    # 相同行业
    if industry1 == industry2:
        return 1.0

    # 检查关联行业
    related_industries = INDUSTRY_RELATIONS.get(industry1, [])
    if industry2 in related_industries:
        return 0.7

    # 检查反向关联
    related_industries = INDUSTRY_RELATIONS.get(industry2, [])
    if industry1 in related_industries:
        return 0.7

    return 0.3  # 无关行业


# ==================== 评分权重配置 ====================
SCORING_WEIGHTS = {
    "skill": 0.35,
    "experience": 0.25,
    "culture": 0.15,
    "salary": 0.15,
    "trajectory": 0.10,
}


# ==================== 评分结果 ====================
@dataclass
class DimensionScore:
    """单一维度分数"""
    dimension: str
    score: float
    details: str = ""
    matched_items: list = field(default_factory=list)
    unmatched_items: list = field(default_factory=list)


@dataclass
class ScoringResult:
    """综合评分结果"""
    candidate_id: str
    job_id: str

    # 各维度分数
    skill_score: DimensionScore
    experience_score: DimensionScore
    culture_score: DimensionScore
    salary_score: DimensionScore
    trajectory_score: DimensionScore

    # 综合分数
    overall_score: float = 0.0

    # 匹配原因
    match_reasons: list = field(default_factory=list)

    # 过滤原因 (如果有)
    filtered_reason: Optional[str] = None

    def __post_init__(self):
        """计算综合分数"""
        self.overall_score = (
            self.skill_score.score * SCORING_WEIGHTS["skill"] +
            self.experience_score.score * SCORING_WEIGHTS["experience"] +
            self.culture_score.score * SCORING_WEIGHTS["culture"] +
            self.salary_score.score * SCORING_WEIGHTS["salary"] +
            self.trajectory_score.score * SCORING_WEIGHTS["trajectory"]
        )


# ==================== 评分函数 ====================

def score_skill_match(
    job_skills: list[str],
    candidate_skills: list[str],
    core_skills: Optional[list[str]] = None,
) -> DimensionScore:
    """
    技能匹配评分

    使用 Jaccard 相似度计算技能匹配度。
    核心技能权重 x2。

    Jaccard = |A ∩ B| / |A ∪ B|

    Args:
        job_skills: 岗位所需技能列表
        candidate_skills: 候选人技能列表
        core_skills: 核心技能列表 (权重 x2)

    Returns:
        DimensionScore
    """
    if not job_skills or not candidate_skills:
        return DimensionScore(
            dimension="skill",
            score=0.0,
            details="缺少技能信息"
        )

    # 标准化技能名称 (小写 + 去空格)
    job_skills_set = set(s.lower().strip() for s in job_skills)
    candidate_skills_set = set(s.lower().strip() for s in candidate_skills)

    # 计算交集
    intersection = job_skills_set & candidate_skills_set

    # 计算 Jaccard
    union = job_skills_set | candidate_skills_set
    if not union:
        jaccard = 0.0
    else:
        jaccard = len(intersection) / len(union)

    # 核心技能加分
    core_bonus = 0.0
    matched_core = []
    unmatched_core = []

    if core_skills:
        core_skills_set = set(s.lower().strip() for s in core_skills)
        matched_core = list(intersection & core_skills_set)
        unmatched_core = list(core_skills_set - intersection)

        # 核心技能匹配度 (每个 +0.1，上限 0.2)
        if len(core_skills_set) > 0:
            core_match_rate = len(matched_core) / len(core_skills_set)
            core_bonus = min(0.2, core_match_rate * 0.2)

    # 最终分数 (Jaccard + 核心技能加分)
    final_score = min(1.0, jaccard + core_bonus)

    matched_items = list(intersection)
    unmatched_items = list(job_skills_set - candidate_skills_set)

    details = f"Jaccard={jaccard:.3f}, CoreBonus={core_bonus:.3f}"

    return DimensionScore(
        dimension="skill",
        score=final_score,
        details=details,
        matched_items=matched_items,
        unmatched_items=unmatched_items,
    )


def score_experience_match(
    job_years_min: int,
    job_years_max: int,
    candidate_years: int,
) -> DimensionScore:
    """
    工作经验匹配评分

    - 完全在范围内: 1.0
    - 超过上限: 线性衰减
    - 低于下限: 线性衰减

    Args:
        job_years_min: 岗位最低年限要求
        job_years_max: 岗位最高年限要求
        candidate_years: 候选人工作年限

    Returns:
        DimensionScore
    """
    # 无明确要求
    if job_years_min == 0 and job_years_max == 0:
        return DimensionScore(
            dimension="experience",
            score=1.0,
            details="岗位无年限要求"
        )

    # 在范围内
    if job_years_min <= candidate_years <= job_years_max:
        return DimensionScore(
            dimension="experience",
            score=1.0,
            details=f"候选人有{candidate_years}年经验，符合要求"
        )

    # 低于下限
    if candidate_years < job_years_min:
        deficit = job_years_min - candidate_years
        # 每少1年扣 0.1，最低 0.2
        score = max(0.2, 1.0 - deficit * 0.1)
        return DimensionScore(
            dimension="experience",
            score=score,
            details=f"经验不足{deficit}年 (要求≥{job_years_min}年，实际{candidate_years}年)"
        )

    # 超过上限
    if candidate_years > job_years_max:
        excess = candidate_years - job_years_max
        # 每多1年扣 0.05，最低 0.5
        score = max(0.5, 1.0 - excess * 0.05)
        return DimensionScore(
            dimension="experience",
            score=score,
            details=f"经验超过上限{excess}年 (要求≤{job_years_max}年，实际{candidate_years}年)"
        )

    return DimensionScore(
        dimension="experience",
        score=0.5,
        details="经验评分异常"
    )


def score_culture_fit(
    job_industries: list[str],
    candidate_industries: list[str],
) -> DimensionScore:
    """
    文化契合度评分 (行业匹配)

    - 同行业: 1.0
    - 相关行业: 0.7
    - 无关行业: 0.3

    Args:
        job_industries: 岗位目标行业列表
        candidate_industries: 候选人期望行业列表

    Returns:
        DimensionScore
    """
    if not job_industries or not candidate_industries:
        return DimensionScore(
            dimension="culture",
            score=0.5,
            details="缺少行业信息"
        )

    # 计算最佳匹配度
    best_match = 0.0
    match_details = []

    for job_industry in job_industries:
        for candidate_industry in candidate_industries:
            relationship = get_industry_relationship(job_industry, candidate_industry)
            if relationship > best_match:
                best_match = relationship
            match_details.append(f"{candidate_industry}->{job_industry}:{relationship:.1f}")

    return DimensionScore(
        dimension="culture",
        score=best_match,
        details="; ".join(match_details[:3]),  # 最多显示3条
    )


def score_salary_match(
    job_salary_min: int,
    job_salary_max: int,
    candidate_salary_min: int,
    candidate_salary_max: int,
) -> DimensionScore:
    """
    薪资匹配评分

    按重叠比例计算薪资匹配度。

    Args:
        job_salary_min: 岗位最低薪资 (分/月)
        job_salary_max: 岗位最高薪资 (分/月)
        candidate_salary_min: 候选人期望最低薪资 (分/月)
        candidate_salary_max: 候选人期望最高薪资 (分/月)

    Returns:
        DimensionScore
    """
    # 处理 0 值
    if job_salary_min == 0:
        job_salary_min = job_salary_max
    if job_salary_max == 0:
        job_salary_max = job_salary_min * 2 if job_salary_min else 100000

    if candidate_salary_min == 0:
        candidate_salary_min = candidate_salary_max
    if candidate_salary_max == 0:
        candidate_salary_max = candidate_salary_min * 2 if candidate_salary_min else 100000

    # 无薪资信息
    if job_salary_min == 0 and candidate_salary_min == 0:
        return DimensionScore(
            dimension="salary",
            score=1.0,
            details="双方均未提供薪资信息"
        )

    # 只有岗位薪资
    if candidate_salary_min == 0:
        if job_salary_min <= candidate_salary_max:
            return DimensionScore(
                dimension="salary",
                score=1.0,
                details=f"岗位薪资 {job_salary_min//1000}K-{job_salary_max//1000}K"
            )
        else:
            score = max(0.3, candidate_salary_max / job_salary_min)
            return DimensionScore(
                dimension="salary",
                score=score,
                details="候选人薪资期望低于岗位范围"
            )

    # 只有候选人薪资
    if job_salary_min == 0:
        if candidate_salary_min <= job_salary_max:
            return DimensionScore(
                dimension="salary",
                score=1.0,
                details=f"候选人期望 {candidate_salary_min//1000}K-{candidate_salary_max//1000}K"
            )
        else:
            score = max(0.3, job_salary_max / candidate_salary_min)
            return DimensionScore(
                dimension="salary",
                score=score,
                details="候选人期望高于岗位范围"
            )

    # 计算重叠区域
    overlap_min = max(job_salary_min, candidate_salary_min)
    overlap_max = min(job_salary_max, candidate_salary_max)

    if overlap_min <= overlap_max:
        # 有重叠
        overlap_range = overlap_max - overlap_min
        job_range = job_salary_max - job_salary_min
        candidate_range = candidate_salary_max - candidate_salary_min

        if job_range > 0 and candidate_range > 0:
            overlap_ratio = overlap_range / min(job_range, candidate_range)
            score = min(1.0, overlap_ratio)
        else:
            score = 1.0

        details = f"薪资重叠 {overlap_min//1000}K-{overlap_max//1000}K"
    else:
        # 无重叠
        gap = overlap_min - overlap_max
        avg_salary = (job_salary_max + candidate_salary_max) / 2

        if avg_salary > 0:
            gap_ratio = gap / avg_salary
            score = max(0.0, 1.0 - gap_ratio)
        else:
            score = 0.0

        details = f"薪资不匹配，差距 {gap//1000}K"

    return DimensionScore(
        dimension="salary",
        score=score,
        details=details,
    )


def score_trajectory(
    work_history: list[dict],
    target_industry: str,
) -> DimensionScore:
    """
    职业轨迹评分

    分析职业上升轨迹:
    - 薪资提升
    - 公司 tier 提升
    - 职位层级提升

    Args:
        work_history: 工作经历列表
        target_industry: 目标行业

    Returns:
        DimensionScore
    """
    if not work_history or len(work_history) < 1:
        return DimensionScore(
            dimension="trajectory",
            score=0.5,
            details="缺少工作经历"
        )

    # 公司 tier 映射 (简化)
    TIER_MAPPING = {
        "tier1": ["腾讯", "阿里", "字节", "百度", "美团", "京东", "华为", "字节跳动"],
        "tier2": ["快手", "滴滴", "拼多多", "网易", "新浪", "搜狐", "小米"],
        "tier3": ["其他知名企业"],
        "default": ["中小企业"],
    }

    def get_company_tier(company_name: str) -> int:
        """获取公司 tier"""
        for tier, keywords in TIER_MAPPING.items():
            for keyword in keywords:
                if keyword in company_name:
                    if tier == "tier1":
                        return 4
                    elif tier == "tier2":
                        return 3
                    elif tier == "tier3":
                        return 2
        return 1

    # 分析轨迹
    trajectory_score = 0.5  # 基础分
    trajectory_details = []

    # 检查公司 tier 变化
    tier_progression = []
    for work in work_history[:3]:  # 最近 3 份工作
        company = work.get("company", "")
        tier = get_company_tier(company)
        tier_progression.append(tier)

    if len(tier_progression) >= 2:
        # 计算 tier 变化趋势
        tier_change = tier_progression[0] - tier_progression[-1]
        if tier_change > 0:
            trajectory_score += 0.2
            trajectory_details.append(f"Tier提升: {tier_progression[-1]}->{tier_progression[0]}")
        elif tier_change < 0:
            trajectory_score -= 0.1
            trajectory_details.append(f"Tier下降")

    # 检查行业转换方向
    latest_industry = None
    for work in work_history[:1]:  # 最近一份工作
        # 简化处理，假设工作经历中包含行业信息
        desc = work.get("description", "")
        for ind in [target_industry] + INDUSTRY_RELATIONS.get(target_industry, []):
            if ind in desc:
                latest_industry = ind
                break

    if latest_industry:
        relationship = get_industry_relationship(latest_industry, target_industry)
        if relationship >= 0.7:
            trajectory_score += 0.15
            trajectory_details.append(f"行业相关: {latest_industry}")
        elif relationship < 0.5:
            trajectory_score -= 0.1
            trajectory_details.append(f"行业转换: {latest_industry}->{target_industry}")

    # 检查职位层级变化
    title_keywords = ["高级", "Senior", "资深", "专家", "Lead", "主管", "Manager", "总监", "Director", "VP"]
    senior_titles = sum(1 for work in work_history[:3] for kw in title_keywords if kw in work.get("title", ""))

    if senior_titles > 0:
        trajectory_score += 0.1
        trajectory_details.append(f"高级职位数: {senior_titles}")

    # 限制范围
    final_score = max(0.0, min(1.0, trajectory_score))

    return DimensionScore(
        dimension="trajectory",
        score=final_score,
        details="; ".join(trajectory_details) if trajectory_details else "轨迹平稳",
    )


# ==================== 综合评分入口 ====================
def calculate_match_score(
    job_data: dict,
    candidate_data: dict,
    candidate_id: str,
    job_id: str,
) -> ScoringResult:
    """
    计算候选人与岗位的匹配分数

    Args:
        job_data: 岗位数据
        candidate_data: 候选人数据
        candidate_id: 候选人 ID
        job_id: 岗位 ID

    Returns:
        ScoringResult
    """
    # 提取岗位数据
    job_skills = job_data.get("skills", [])
    core_skills = job_data.get("core_skills", [])
    job_years_min = job_data.get("years_exp_min", 0)
    job_years_max = job_data.get("years_exp_max", 0)
    job_industries = job_data.get("industries", [])
    job_salary_min = job_data.get("salary_min", 0)
    job_salary_max = job_data.get("salary_max", 0)

    # 提取候选人数据
    candidate_skills = candidate_data.get("skills", [])
    candidate_years = candidate_data.get("total_years_exp", 0)
    candidate_industries = candidate_data.get("preferred_industries", [])
    candidate_salary_min = candidate_data.get("expected_salary_min", 0)
    candidate_salary_max = candidate_data.get("expected_salary_max", 0)
    work_history = candidate_data.get("work_history", [])

    # 计算各维度分数
    skill_score = score_skill_match(job_skills, candidate_skills, core_skills)
    experience_score = score_experience_match(job_years_min, job_years_max, candidate_years)
    culture_score = score_culture_fit(job_industries, candidate_industries)
    salary_score = score_salary_match(job_salary_min, job_salary_max, candidate_salary_min, candidate_salary_max)
    trajectory_score = score_trajectory(work_history, job_industries[0] if job_industries else "")

    # 构建结果
    result = ScoringResult(
        candidate_id=candidate_id,
        job_id=job_id,
        skill_score=skill_score,
        experience_score=experience_score,
        culture_score=culture_score,
        salary_score=salary_score,
        trajectory_score=trajectory_score,
    )

    # 生成匹配原因
    result.match_reasons = _generate_match_reasons(result)

    return result


def _generate_match_reasons(result: ScoringResult) -> list[str]:
    """生成匹配原因列表"""
    reasons = []

    # 技能匹配
    if result.skill_score.score >= 0.7:
        matched = result.skill_score.matched_items[:3]
        if matched:
            reasons.append(f"技能匹配度高: {', '.join(matched)}")

    # 经验匹配
    if result.experience_score.score >= 0.9:
        reasons.append(f"工作经验符合要求")

    # 文化契合
    if result.culture_score.score >= 0.8:
        reasons.append("行业背景契合")

    # 薪资匹配
    if result.salary_score.score >= 0.8:
        reasons.append("薪资期望匹配")

    # 职业轨迹
    if result.trajectory_score.score >= 0.6:
        details = result.trajectory_score.details
        if details and details != "轨迹平稳":
            reasons.append(f"职业发展良好")

    return reasons


# ==================== 批量评分 ====================
def batch_score_candidates(
    job_data: dict,
    candidates_data: list[dict],
    job_id: str,
) -> list[ScoringResult]:
    """
    批量计算候选人与岗位的匹配分数

    Args:
        job_data: 岗位数据
        candidates_data: 候选人数据列表
        job_id: 岗位 ID

    Returns:
        按分数降序排列的结果列表
    """
    results = []

    for candidate in candidates_data:
        candidate_id = candidate.get("id", "")
        if not candidate_id:
            continue

        result = calculate_match_score(
            job_data=job_data,
            candidate_data=candidate,
            candidate_id=candidate_id,
            job_id=job_id,
        )

        # 过滤验证分数低于 0.6 的候选人
        verification_score = candidate.get("verification_score", 1.0)
        if verification_score < 0.6:
            result.filtered_reason = f"验证分数不足: {verification_score:.2f} < 0.60"

        results.append(result)

    # 按综合分数降序排列
    results.sort(key=lambda x: x.overall_score, reverse=True)

    return results


# ==================== 导出 ====================
__all__ = [
    "SCORING_WEIGHTS",
    "DimensionScore",
    "ScoringResult",
    "score_skill_match",
    "score_experience_match",
    "score_culture_fit",
    "score_salary_match",
    "score_trajectory",
    "calculate_match_score",
    "batch_score_candidates",
    "get_industry_relationship",
]
