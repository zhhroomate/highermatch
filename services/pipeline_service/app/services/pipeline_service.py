"""
HigherMatch™ Pipeline Service - Pipeline Service
===============================================

招聘管道管理业务逻辑层。

提供:
- 获取岗位招聘管道 (按阶段分组)
- 移动候选人到不同阶段
- WebSocket 广播事件

版本: 1.0.0
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from shared.models import MatchResult, Job, Candidate, Employer, PipelineStage as ModelPipelineStage
from app.schemas.pipeline import (
    PipelineStage,
    PipelineCard,
    PipelineColumn,
    PipelineResponse,
    PipelineMoveResponse,
    CandidateBrief,
    ScoreBreakdown,
)


# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== WebSocket 广播服务 ====================


class WebSocketBroadcaster:
    """
    WebSocket 广播服务

    负责向连接的客户广播管道更新事件。
    当前为占位实现，日志记录广播事件。
    """

    def __init__(self) -> None:
        """初始化广播服务"""
        self._connections: dict = {}  # 存储 WebSocket 连接

    async def broadcast(
        self,
        event_type: str,
        data: dict,
        employer_id: Optional[str] = None,
    ) -> None:
        """
        广播事件

        Args:
            event_type: 事件类型 (如 pipeline.moved)
            data: 事件数据
            employer_id: 雇主 ID (用于筛选接收者)
        """
        # 日志占位实现
        logger.info(
            f"WebSocket Broadcast: type={event_type}, "
            f"employer_id={employer_id}, data={data}"
        )

        # TODO: 实际实现 WebSocket 广播
        # for connection in self._connections.values():
        #     if employer_id is None or connection.employer_id == employer_id:
        #         await connection.send_json({
        #             "type": event_type,
        #             "data": data,
        #         })

    async def register(
        self,
        connection_id: str,
        employer_id: str,
        websocket,
    ) -> None:
        """
        注册 WebSocket 连接

        Args:
            connection_id: 连接 ID
            employer_id: 雇主 ID
            websocket: WebSocket 对象
        """
        self._connections[connection_id] = {
            "employer_id": employer_id,
            "websocket": websocket,
        }
        logger.info(f"WebSocket connected: {connection_id} for employer {employer_id}")

    async def unregister(self, connection_id: str) -> None:
        """
        注销 WebSocket 连接

        Args:
            connection_id: 连接 ID
        """
        if connection_id in self._connections:
            del self._connections[connection_id]
            logger.info(f"WebSocket disconnected: {connection_id}")


# 全局广播器实例
_broadcaster: Optional[WebSocketBroadcaster] = None


def get_broadcaster() -> WebSocketBroadcaster:
    """获取广播器实例"""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = WebSocketBroadcaster()
    return _broadcaster


# ==================== 管道仓储 ====================


class PipelineRepository:
    """
    管道仓储

    处理管道相关的数据库查询和操作。
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化仓储

        Args:
            db: 数据库会话
        """
        self.db = db

    async def get_job_with_employer(self, job_id: uuid.UUID) -> Optional[Job]:
        """
        获取岗位及其雇主信息

        Args:
            job_id: 岗位 ID

        Returns:
            Job 对象或 None
        """
        stmt = (
            select(Job)
            .options(joinedload(Job.employer))
            .where(
                and_(
                    Job.id == job_id,
                    Job.is_deleted == False
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_match_result_with_details(
        self,
        match_id: uuid.UUID,
    ) -> Optional[MatchResult]:
        """
        获取匹配记录 (包含候选人和岗位信息)

        Args:
            match_id: 匹配记录 ID

        Returns:
            MatchResult 对象或 None
        """
        stmt = (
            select(MatchResult)
            .options(
                joinedload(MatchResult.candidate),
                joinedload(MatchResult.job),
                joinedload(MatchResult.employer),
            )
            .where(
                and_(
                    MatchResult.id == match_id,
                    MatchResult.is_deleted == False
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_matches_by_job(
        self,
        job_id: uuid.UUID,
    ) -> list[MatchResult]:
        """
        获取岗位的所有匹配记录

        Args:
            job_id: 岗位 ID

        Returns:
            MatchResult 列表
        """
        stmt = (
            select(MatchResult)
            .options(
                joinedload(MatchResult.candidate),
            )
            .where(
                and_(
                    MatchResult.job_id == job_id,
                    MatchResult.is_deleted == False
                )
            )
            .order_by(MatchResult.overall_score.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def update_pipeline_stage(
        self,
        match_id: uuid.UUID,
        from_stage: str,
        to_stage: str,
    ) -> Optional[MatchResult]:
        """
        更新匹配记录的管道阶段

        Args:
            match_id: 匹配记录 ID
            from_stage: 原阶段
            to_stage: 目标阶段

        Returns:
            更新后的 MatchResult 或 None
        """
        stmt = (
            select(MatchResult)
            .options(
                joinedload(MatchResult.candidate),
                joinedload(MatchResult.job),
            )
            .where(
                and_(
                    MatchResult.id == match_id,
                    MatchResult.pipeline_stage == from_stage,
                    MatchResult.is_deleted == False
                )
            )
        )
        result = await self.db.execute(stmt)
        match = result.unique().scalar_one_or_none()

        if not match:
            return None

        # 更新阶段
        match.pipeline_stage = to_stage
        match.updated_at = datetime.now(timezone.utc)

        # 追加时间线记录
        timeline_entry = {
            "action": "stage_changed",
            "from_stage": from_stage,
            "to_stage": to_stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if match.timeline is None:
            match.timeline = []
        match.timeline.append(timeline_entry)

        await self.db.flush()
        await self.db.refresh(match)

        return match


# ==================== 管道服务 ====================


class PipelineService:
    """
    管道服务

    处理招聘管道的业务逻辑。
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.repository = PipelineRepository(db)
        self.broadcaster = get_broadcaster()

    def _extract_years_exp(self, profile: dict) -> Optional[int]:
        """从 profile 中提取工作年限"""
        if isinstance(profile, dict):
            return profile.get("years_exp")
        return None

    def _extract_skills(self, profile: dict) -> list[str]:
        """从 profile 中提取核心技能"""
        if isinstance(profile, dict):
            return profile.get("skills", [])[:5]  # 最多返回5个技能
        return []

    def _candidate_to_brief(self, candidate: Candidate) -> CandidateBrief:
        """将 Candidate 模型转换为 CandidateBrief"""
        profile = candidate.profile or {}
        return CandidateBrief(
            candidate_id=str(candidate.id),
            name=candidate.name,
            avatar_url=candidate.avatar_url,
            current_city=candidate.current_city,
            current_province=candidate.current_province,
            years_exp=self._extract_years_exp(profile),
            skills=self._extract_skills(profile),
            profile_completeness=candidate.profile_completeness or 0.0,
            verification_score=candidate.verification_score,
        )

    def _score_breakdown_to_model(self, breakdown: dict) -> ScoreBreakdown:
        """将分数细分字典转换为 ScoreBreakdown 模型"""
        if not isinstance(breakdown, dict):
            return ScoreBreakdown()

        return ScoreBreakdown(
            skill_match=breakdown.get("skill_match"),
            experience_match=breakdown.get("experience_match"),
            location_match=breakdown.get("location_match"),
            salary_match=breakdown.get("salary_match"),
            culture_match=breakdown.get("culture_match"),
        )

    def _match_to_card(self, match: MatchResult) -> PipelineCard:
        """将 MatchResult 转换为 PipelineCard"""
        # 转换旧版阶段名称
        stage = PipelineStage.from_legacy(match.pipeline_stage)

        return PipelineCard(
            match_id=str(match.id),
            candidate=self._candidate_to_brief(match.candidate),
            overall_score=match.overall_score,
            score_breakdown=self._score_breakdown_to_model(match.score_breakdown or {}),
            ai_recommendation=match.ai_recommendation,
            match_reasons=match.match_reasons or [],
            pipeline_stage=stage,
            timeline=match.timeline or [],
            created_at=match.created_at,
            updated_at=match.updated_at,
        )

    async def get_pipeline(
        self,
        job_id: str,
        employer_id: str,
    ) -> PipelineResponse:
        """
        获取岗位招聘管道

        按 pipeline_stage 分组返回候选人卡片列表。

        Args:
            job_id: 岗位 ID
            employer_id: 雇主 ID (用于权限验证)

        Returns:
            PipelineResponse

        Raises:
            ValueError: 岗位不存在或无权访问
        """
        job_uuid = uuid.UUID(job_id)

        # 验证岗位存在
        job = await self.repository.get_job_with_employer(job_uuid)
        if not job:
            raise ValueError("岗位不存在")

        # 验证权限: 只有发布该岗位的雇主可以访问
        if str(job.employer_id) != employer_id:
            raise PermissionError("无权访问此岗位的招聘管道")

        # 获取所有匹配记录
        matches = await self.repository.get_matches_by_job(job_uuid)

        # 按阶段分组
        stage_columns: dict[PipelineStage, list[PipelineCard]] = {
            stage: [] for stage in PipelineStage.kanban_stages()
        }

        for match in matches:
            card = self._match_to_card(match)
            stage = PipelineStage.from_legacy(match.pipeline_stage)
            if stage in stage_columns:
                stage_columns[stage].append(card)

        # 构建响应
        columns = [
            PipelineColumn(
                stage=stage,
                cards=cards,
                count=len(cards),
            )
            for stage, cards in stage_columns.items()
        ]

        total_candidates = sum(col.count for col in columns)

        return PipelineResponse(
            job_id=str(job.id),
            job_title=job.job_title,
            columns=columns,
            total_candidates=total_candidates,
        )

    async def move_candidate(
        self,
        match_id: str,
        from_stage: PipelineStage,
        to_stage: PipelineStage,
        employer_id: str,
    ) -> PipelineMoveResponse:
        """
        移动候选人到不同阶段

        Args:
            match_id: 匹配记录 ID
            from_stage: 原阶段
            to_stage: 目标阶段
            employer_id: 雇主 ID (用于权限验证)

        Returns:
            PipelineMoveResponse

        Raises:
            ValueError: 匹配记录不存在
            PermissionError: 无权操作此记录
            ValueError: 阶段不匹配
        """
        match_uuid = uuid.UUID(match_id)

        # 获取匹配记录
        match = await self.repository.get_match_result_with_details(match_uuid)
        if not match:
            raise ValueError("匹配记录不存在")

        # 验证权限: 只有该岗位的雇主可以操作
        if str(match.employer_id) != employer_id:
            raise PermissionError("无权操作此候选人")

        # 验证当前阶段
        current_stage = PipelineStage.from_legacy(match.pipeline_stage)
        if current_stage != from_stage:
            raise ValueError(
                f"候选人当前不在 '{from_stage.value}' 阶段，"
                f"实际在 '{current_stage.value}' 阶段"
            )

        # 更新阶段
        updated_match = await self.repository.update_pipeline_stage(
            match_uuid,
            from_stage.value,
            to_stage.value,
        )

        if not updated_match:
            raise ValueError("移动操作失败")

        # 广播 WebSocket 事件
        await self.broadcaster.broadcast(
            event_type="pipeline.moved",
            data={
                "match_id": match_id,
                "job_id": str(match.job_id),
                "from_stage": from_stage.value,
                "to_stage": to_stage.value,
                "candidate_id": str(match.candidate_id),
                "employer_id": employer_id,
            },
            employer_id=employer_id,
        )

        logger.info(
            f"Pipeline move: match_id={match_id}, "
            f"{from_stage.value} -> {to_stage.value}, "
            f"employer_id={employer_id}"
        )

        return PipelineMoveResponse(
            match_id=match_id,
            from_stage=from_stage,
            to_stage=to_stage,
            updated_at=updated_match.updated_at,
            message=f"已从 '{from_stage.value}' 移动到 '{to_stage.value}'",
        )


# ==================== 导出 ====================
__all__ = [
    "PipelineRepository",
    "PipelineService",
    "WebSocketBroadcaster",
    "get_broadcaster",
]
