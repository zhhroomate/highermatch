"""
HigherMatch™ Candidate Service - Candidates Router
==================================================

候选人相关 API 路由。

接口:
1. POST /api/v1/resume/parse - 简历解析
2. GET /api/v1/candidates/profile - 获取候选人档案
3. PUT /api/v1/candidates/profile - 更新候选人档案
4. GET /api/v1/candidates/recommendations - 获取职位推荐
5. POST /api/v1/applications - 创建申请

版本: 1.0.0
"""

import logging
import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

import sys
sys.path.insert(0, "/workspace/highermatch")
from shared.auth_middleware import get_current_user, TokenPayload, require_role
from shared.models import Candidate, MatchResult, PipelineStage, Job

from app.main import get_db, get_kafka_producer
from app.schemas.candidate import (
    ResumeParseResponse,
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
    CandidateProfileUpdateResponse,
    CandidateRecommendationsResponse,
    RecommendedJob,
    ApplicationCreateRequest,
    ApplicationResponse,
    EducationItem,
    WorkHistoryItem,
)
from app.services.resume_parser import get_resume_parser

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)

# ==================== 路由实例 ====================
router = APIRouter(prefix="/api/v1", tags=["Candidates"])


# ==================== 依赖项 ====================
async def get_candidate_by_user(
    user: Annotated[TokenPayload, Depends(get_current_user)],
    db: "AsyncSession",
) -> Candidate:
    """
    根据当前用户获取候选人记录

    Args:
        user: 当前用户
        db: 数据库会话

    Returns:
        Candidate 模型实例

    Raises:
        HTTPException: 候选人记录不存在
    """
    # 根据用户 ID 查询候选人
    stmt = select(Candidate).where(
        func.cast(Candidate.id, String) == user.sub
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "CANDIDATE_NOT_FOUND",
                    "message": "候选人记录不存在"
                }
            }
        )

    return candidate


# String type for PostgreSQL cast
from sqlalchemy import String


# ==================== 完整度计算 ====================
def calculate_profile_completeness(candidate: Candidate) -> tuple[float, dict]:
    """
    计算资料完整度

    计算规则:
    - 基础信息: 30% (name, email, phone, gender, birth_date)
    - 教育经历: 20% (education 至少 1 条)
    - 工作经历: 30% (work_history 至少 1 条)
    - 技能: 10% (skills 至少 3 个)
    - 偏好: 10% (期望薪资、地点、行业至少填 1 项)

    Args:
        candidate: 候选人实例

    Returns:
        (完整度, 明细字典)
    """
    weights = {
        "basic_info": 0.30,
        "education": 0.20,
        "work_history": 0.30,
        "skills": 0.10,
        "preferences": 0.10,
    }

    scores = {}
    total_score = 0.0

    # 基础信息 (30%)
    basic_fields = [
        candidate.name,
        candidate.email,
        candidate.profile.get("phone") if candidate.profile else None,
        candidate.gender,
        candidate.birth_date,
    ]
    basic_score = sum(1 for f in basic_fields if f is not None) / len(basic_fields)
    scores["basic_info"] = round(basic_score, 2)
    total_score += basic_score * weights["basic_info"]

    # 教育经历 (20%)
    education = candidate.profile.get("education", []) if candidate.profile else []
    education_score = 1.0 if len(education) > 0 else 0.0
    scores["education"] = education_score
    total_score += education_score * weights["education"]

    # 工作经历 (30%)
    work_history = candidate.profile.get("work_history", []) if candidate.profile else []
    work_score = 1.0 if len(work_history) > 0 else 0.0
    scores["work_history"] = work_score
    total_score += work_score * weights["work_history"]

    # 技能 (10%)
    skills = candidate.profile.get("skills", []) if candidate.profile else []
    skills_score = min(1.0, len(skills) / 3) if len(skills) > 0 else 0.0
    scores["skills"] = round(skills_score, 2)
    total_score += skills_score * weights["skills"]

    # 偏好 (10%)
    pref_fields = [
        candidate.expected_salary_min,
        candidate.expected_salary_max,
        candidate.preferred_locations,
        candidate.preferred_industries,
    ]
    pref_score = sum(1 for f in pref_fields if f) / len(pref_fields)
    scores["preferences"] = round(pref_score, 2)
    total_score += pref_score * weights["preferences"]

    return round(total_score, 2), scores


# ==================== 1. 简历解析接口 ====================
@router.post(
    "/resume/parse",
    response_model=ResumeParseResponse,
    summary="解析简历",
    description="上传 PDF 文件，解析简历内容并提取结构化信息"
)
async def parse_resume(
    file: Annotated[UploadFile, File(description="PDF 文件，最大 10MB")],
    candidate_id: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    解析上传的简历文件

    - 使用 PyMuPDF (fitz) 提取 PDF 文本
    - 调用 LLM 将文本解析为 JSON 结构
    - 返回教育经历、工作经历、技能等信息
    """
    # 验证文件类型
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_FILE_TYPE",
                    "message": "仅支持 PDF 格式文件"
                }
            }
        )

    # 读取文件内容
    content = await file.read()

    # 生成简历 ID
    resume_id = str(uuid.uuid4())

    # 解析简历
    parser = get_resume_parser()
    result = await parser.parse_resume(
        content=content,
        filename=file.filename,
        candidate_id=candidate_id,
        resume_id=resume_id,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "error": {
                    "code": "PARSE_FAILED",
                    "message": result.error or "简历解析失败"
                }
            }
        )

    # 返回解析结果
    return ResumeParseResponse(
        success=True,
        candidate_id=candidate_id,
        resume_id=resume_id,
        data=result.parsed_data.model_dump() if result.parsed_data else None,
        from_cache=result.from_cache,
    )


# ==================== 2. 获取候选人档案 ====================
@router.get(
    "/candidates/profile",
    response_model=CandidateProfileResponse,
    summary="获取候选人档案",
    description="获取当前登录候选人的完整档案信息"
)
async def get_profile(
    user: Annotated[TokenPayload, Depends(require_role(["candidate"]))],
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前候选人的档案

    需要 candidate 角色权限。

    返回:
    - 基本信息
    - 教育经历、工作经历
    - 技能列表
    - 期望工作偏好
    - 资料完整度 (动态计算)
    """
    # 查询候选人记录
    stmt = select(Candidate).where(
        func.cast(Candidate.id, String) == user.sub
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "CANDIDATE_NOT_FOUND",
                    "message": "候选人记录不存在"
                }
            }
        )

    # 计算完整度
    completeness, breakdown = calculate_profile_completeness(candidate)

    # 解析画像数据
    profile_data = candidate.profile or {}
    education_list = [
        EducationItem(**edu) for edu in profile_data.get("education", [])
        if isinstance(edu, dict)
    ]
    work_history_list = [
        WorkHistoryItem(**work) for work in profile_data.get("work_history", [])
        if isinstance(work, dict)
    ]

    return CandidateProfileResponse(
        user_id=str(candidate.id),
        name=candidate.name,
        email=candidate.email,
        phone=profile_data.get("phone"),
        avatar_url=candidate.avatar_url,
        gender=candidate.gender,
        age=candidate.age,
        birth_date=candidate.birth_date,
        current_province=candidate.current_province,
        current_city=candidate.current_city,
        current_district=candidate.current_district,
        job_search_status=candidate.job_search_status,
        education=education_list,
        work_history=work_history_list,
        skills=profile_data.get("skills", []),
        certifications=profile_data.get("certifications", []),
        summary=profile_data.get("summary"),
        total_years_exp=profile_data.get("total_years_exp", 0),
        resume_id=str(candidate.resume_id) if candidate.resume_id else None,
        resume_url=candidate.resume_url,
        resume_parsed_at=candidate.resume_parsed_at,
        expected_salary_min=candidate.expected_salary_min,
        expected_salary_max=candidate.expected_salary_max,
        preferred_job_titles=candidate.preferred_job_titles or [],
        preferred_locations=candidate.preferred_locations or [],
        preferred_industries=candidate.preferred_industries or [],
        profile_completeness=completeness,
        completeness_breakdown=breakdown,
        is_active=candidate.is_active,
        is_verified=candidate.verification_score is not None and candidate.verification_score > 0,
        verification_score=candidate.verification_score,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


# ==================== 3. 更新候选人档案 ====================
@router.put(
    "/candidates/profile",
    response_model=CandidateProfileUpdateResponse,
    summary="更新候选人档案",
    description="更新当前登录候选人的档案信息"
)
async def update_profile(
    request: CandidateProfileUpdateRequest,
    user: Annotated[TokenPayload, Depends(require_role(["candidate"]))],
    db: AsyncSession = Depends(get_db),
    kafka_producer: Any = Depends(get_kafka_producer),
):
    """
    更新候选人档案

    需要 candidate 角色权限。

    支持部分更新，只传入需要修改的字段。
    更新后触发 Kafka 消息: topic=candidate.updated
    """
    # 查询候选人记录
    stmt = select(Candidate).where(
        func.cast(Candidate.id, String) == user.sub
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "CANDIDATE_NOT_FOUND",
                    "message": "候选人记录不存在"
                }
            }
        )

    # 记录更新的字段
    updated_fields = []

    # 更新基本信息
    if request.name is not None:
        candidate.name = request.name
        updated_fields.append("name")
    if request.avatar_url is not None:
        candidate.avatar_url = request.avatar_url
        updated_fields.append("avatar_url")
    if request.gender is not None:
        candidate.gender = request.gender
        updated_fields.append("gender")
    if request.birth_date is not None:
        candidate.birth_date = request.birth_date
        updated_fields.append("birth_date")

    # 更新地理位置
    if request.current_province is not None:
        candidate.current_province = request.current_province
        updated_fields.append("current_province")
    if request.current_city is not None:
        candidate.current_city = request.current_city
        updated_fields.append("current_city")
    if request.current_district is not None:
        candidate.current_district = request.current_district
        updated_fields.append("current_district")

    # 更新求职状态
    if request.job_search_status is not None:
        candidate.job_search_status = request.job_search_status
        updated_fields.append("job_search_status")

    # 更新画像数据 (需要合并)
    profile = candidate.profile or {}
    if request.education is not None:
        profile["education"] = [edu.model_dump() for edu in request.education]
        updated_fields.append("education")
    if request.work_history is not None:
        profile["work_history"] = [work.model_dump() for work in request.work_history]
        updated_fields.append("work_history")
    if request.skills is not None:
        profile["skills"] = request.skills
        updated_fields.append("skills")
    if request.certifications is not None:
        profile["certifications"] = request.certifications
        updated_fields.append("certifications")
    if request.summary is not None:
        profile["summary"] = request.summary
        updated_fields.append("summary")

    candidate.profile = profile

    # 更新期望工作
    if request.expected_salary_min is not None:
        candidate.expected_salary_min = request.expected_salary_min
        updated_fields.append("expected_salary_min")
    if request.expected_salary_max is not None:
        candidate.expected_salary_max = request.expected_salary_max
        updated_fields.append("expected_salary_max")
    if request.preferred_job_titles is not None:
        candidate.preferred_job_titles = request.preferred_job_titles
        updated_fields.append("preferred_job_titles")
    if request.preferred_locations is not None:
        candidate.preferred_locations = request.preferred_locations
        updated_fields.append("preferred_locations")
    if request.preferred_industries is not None:
        candidate.preferred_industries = request.preferred_industries
        updated_fields.append("preferred_industries")

    # 重新计算完整度
    completeness, _ = calculate_profile_completeness(candidate)
    candidate.profile_completeness = completeness

    # 提交更新
    await db.commit()
    await db.refresh(candidate)

    # 发送 Kafka 消息
    if kafka_producer:
        try:
            await kafka_producer.send(
                topic="candidate.updated",
                value={
                    "candidate_id": str(candidate.id),
                    "updated_fields": updated_fields,
                    "timestamp": candidate.updated_at.isoformat(),
                }
            )
            logger.info(f"Kafka message sent: candidate.updated for {candidate.id}")
        except Exception as e:
            logger.warning(f"Failed to send Kafka message: {e}")

    return CandidateProfileUpdateResponse(
        success=True,
        message="档案更新成功",
        updated_fields=updated_fields,
        profile_completeness=completeness,
    )


# ==================== 4. 获取职位推荐 ====================
@router.get(
    "/candidates/recommendations",
    response_model=CandidateRecommendationsResponse,
    summary="获取职位推荐",
    description="根据候选人画像反向查询推荐岗位"
)
async def get_recommendations(
    user: Annotated[TokenPayload, Depends(require_role(["candidate"]))],
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    获取职位推荐

    需要 candidate 角色权限。

    调用 vdb_service 的 search_candidates 反向查询推荐岗位。
    返回与候选人画像最匹配的职位列表。
    """
    # 查询候选人记录
    stmt = select(Candidate).where(
        func.cast(Candidate.id, String) == user.sub
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "CANDIDATE_NOT_FOUND",
                    "message": "候选人记录不存在"
                }
            }
        )

    # TODO: 调用 vdb_service 进行向量相似度搜索
    # 目前返回空列表占位
    recommended_jobs: list[RecommendedJob] = []

    # 获取候选人的匹配历史 (作为备选)
    if not recommended_jobs:
        stmt = (
            select(MatchResult, Job)
            .join(Job, MatchResult.job_id == Job.id)
            .where(MatchResult.candidate_id == candidate.id)
            .where(MatchResult.pipeline_stage == PipelineStage.AI_RECOMMENDED)
            .order_by(MatchResult.overall_score.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        rows = result.all()

        for match_result, job in rows:
            recommended_jobs.append(RecommendedJob(
                job_id=str(job.id),
                job_title=job.job_title,
                company_name=job.employer.company_name if job.employer else "未知公司",
                company_logo_url=job.employer.company_logo_url if job.employer else None,
                work_city=job.work_city,
                work_location_type=job.work_location_type or "onsite",
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                employment_type=job.employment_type,
                match_score=match_result.overall_score,
                match_reasons=match_result.match_reasons or [],
                is_urgent=job.is_urgent,
                published_at=job.published_at,
            ))

    return CandidateRecommendationsResponse(
        candidate_id=str(candidate.id),
        total_count=len(recommended_jobs),
        jobs=recommended_jobs,
        search_params={
            "limit": limit,
            "offset": offset,
        },
    )


# ==================== 5. 创建申请 ====================
@router.post(
    "/applications",
    response_model=ApplicationResponse,
    summary="创建申请",
    description="候选人申请职位"
)
async def create_application(
    request: ApplicationCreateRequest,
    user: Annotated[TokenPayload, Depends(require_role(["candidate"]))],
    db: AsyncSession = Depends(get_db),
):
    """
    创建职位申请

    需要 candidate 角色权限。

    在 match_results 表插入记录，stage=ai_recommended。
    确保同一 candidate+job 只能有一条记录。
    """
    # 查询候选人记录
    stmt = select(Candidate).where(
        func.cast(Candidate.id, String) == user.sub
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "CANDIDATE_NOT_FOUND",
                    "message": "候选人记录不存在"
                }
            }
        )

    # 查询职位
    job_uuid = uuid.UUID(request.job_id)
    stmt = select(Job).where(Job.id == job_uuid)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": "职位不存在"
                }
            }
        )

    # 检查是否已申请 (使用 UPSERT 语义)
    stmt = (
        select(MatchResult)
        .where(MatchResult.job_id == job_uuid)
        .where(MatchResult.candidate_id == candidate.id)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # 已存在申请
        return ApplicationResponse(
            success=True,
            application_id=str(existing.id),
            job_id=request.job_id,
            candidate_id=str(candidate.id),
            pipeline_stage=existing.pipeline_stage,
            message="您已申请过该职位",
        )

    # 创建新的申请记录
    match_result = MatchResult(
        job_id=job_uuid,
        candidate_id=candidate.id,
        employer_id=job.employer_id,
        pipeline_stage=PipelineStage.AI_RECOMMENDED,
        overall_score=0.5,  # 初始分数
        score_breakdown={},
        timeline=[
            {
                "action": "applied",
                "timestamp": datetime.utcnow().isoformat(),
                "stage": PipelineStage.AI_RECOMMENDED,
            }
        ],
    )

    db.add(match_result)

    # 更新职位的申请计数
    job.apply_count += 1

    await db.commit()
    await db.refresh(match_result)

    return ApplicationResponse(
        success=True,
        application_id=str(match_result.id),
        job_id=request.job_id,
        candidate_id=str(candidate.id),
        pipeline_stage=match_result.pipeline_stage,
        message="申请成功",
    )


# 需要 datetime
from datetime import datetime


# ==================== 导出 ====================
__all__ = ["router"]
