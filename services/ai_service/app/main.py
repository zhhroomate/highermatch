"""
HigherMatch™ AI 招聘平台 - AI Service
FastAPI 应用入口 - 使用 SQLAlchemy 2.0 Async ORM

版本: 1.0.0
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 配置管理 ====================
class Settings:
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "ai-service")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8004"))
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@postgres:5432/highermatch_dev"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    MATCH_SCORE_THRESHOLD: float = float(os.getenv("MATCH_SCORE_THRESHOLD", "0.75"))

settings = Settings()

# ==================== 数据库配置 ====================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    poolclass=NullPool
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ==================== Pydantic Schemas ====================
class ResumeParseRequest(BaseModel):
    candidate_id: int
    file_path: str | None = None

class ResumeParseResponse(BaseModel):
    candidate_id: int
    skills: list[str]
    experience_years: int | None
    education: str | None
    summary: str | None
    parsed_successfully: bool

class MatchRequest(BaseModel):
    job_id: int
    candidate_id: int

class MatchResponse(BaseModel):
    job_id: int
    candidate_id: int
    match_score: float
    match_details: dict
    ai_explanation: str
    is_recommended: bool

class AIGenerationRequest(BaseModel):
    prompt: str
    context: dict | None = None
    max_tokens: int = 500
    temperature: float = 0.7

class AIGenerationResponse(BaseModel):
    content: str
    model: str
    tokens_used: int | None = None

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = None

class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    suggestions: list[str] = []

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str
    openai_configured: bool

# ==================== 生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME}...")
    logger.info(f"OpenAI API Key configured: {'Yes' if settings.OPENAI_API_KEY else 'No'}")
    yield
    logger.info(f"Shutting down {settings.SERVICE_NAME}...")
    await engine.dispose()

# ==================== FastAPI 应用 ====================
app = FastAPI(
    title="HigherMatch AI Service",
    description="HigherMatch™ AI 招聘平台 - AI 服务 API (简历解析、智能匹配、聊天助手)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== NLU 路由 ====================
from app.routers import nlu

app.include_router(nlu.router)

# ==================== 健康检查路由 ====================
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        service=settings.SERVICE_NAME,
        version="1.0.0",
        database=db_status,
        openai_configured=bool(settings.OPENAI_API_KEY)
    )

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": "HigherMatch AI Service",
        "version": "1.0.0",
        "status": "operational",
        "capabilities": [
            "resume_parsing",
            "candidate_matching",
            "chat_assistant",
            "job_recommendations",
            "nlu_job_parsing"
        ]
    }

# ==================== 简历处理路由 ====================
@app.post("/api/v1/resume/parse", response_model=ResumeParseResponse, tags=["Resume"])
async def parse_resume(
    file: UploadFile = File(...),
    candidate_id: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    解析上传的简历文件 (PDF/DOCX)
    提取技能、工作经验、教育背景等信息
    """
    # TODO: 实现实际的简历解析逻辑
    # 支持 PDF 和 DOCX 格式
    logger.info(f"Parsing resume for candidate {candidate_id}: {file.filename}")

    # 模拟解析结果
    parsed_data = {
        "candidate_id": candidate_id,
        "skills": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
        "experience_years": 3,
        "education": "Bachelor's in Computer Science",
        "summary": "Experienced backend developer with expertise in Python and cloud technologies.",
        "parsed_successfully": True
    }

    # 保存到数据库
    result = await db.execute(
        "INSERT INTO resumes (candidate_id, file_name, parsed_content, skills, experience_years, education, summary) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
        (candidate_id, file.filename, str(parsed_data), parsed_data["skills"],
         parsed_data["experience_years"], parsed_data["education"], parsed_data["summary"])
    )
    resume_id = result.fetchone()[0]
    logger.info(f"Resume saved: ID {resume_id}")

    return ResumeParseResponse(**parsed_data)

# ==================== 匹配服务路由 ====================
@app.post("/api/v1/match/candidate-job", response_model=MatchResponse, tags=["Match"])
async def match_candidate_to_job(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    匹配候选人与职位
    使用 AI 分析简历与职位描述的匹配度
    """
    logger.info(f"Matching candidate {request.candidate_id} to job {request.job_id}")

    # TODO: 接入实际的 AI 匹配逻辑
    # 1. 获取职位信息
    # 2. 获取候选人简历
    # 3. 使用向量数据库进行相似度计算
    # 4. 生成 AI 解释

    # 模拟匹配结果
    match_score = 0.82
    match_details = {
        "skill_match": 0.85,
        "experience_match": 0.75,
        "location_match": 1.0,
        "salary_match": 0.90
    }

    ai_explanation = (
        f"Based on the analysis, this candidate shows strong alignment with the position. "
        f"Key strengths include relevant technical skills ({match_details['skill_match']:.0%} match) "
        f"and appropriate experience level ({match_details['experience_match']:.0%} match)."
    )

    # 保存匹配结果
    result = await db.execute(
        "INSERT INTO matches (job_id, candidate_id, match_score, match_details, ai_explanation) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING id",
        (request.job_id, request.candidate_id, match_score, match_details, ai_explanation)
    )
    match_id = result.fetchone()[0]
    logger.info(f"Match saved: ID {match_id}, Score {match_score}")

    return MatchResponse(
        job_id=request.job_id,
        candidate_id=request.candidate_id,
        match_score=match_score,
        match_details=match_details,
        ai_explanation=ai_explanation,
        is_recommended=match_score >= settings.MATCH_SCORE_THRESHOLD
    )

@app.post("/api/v1/match/recommend-jobs", response_model=list[MatchResponse], tags=["Match"])
async def recommend_jobs_for_candidate(
    candidate_id: int,
    limit: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    为候选人推荐最匹配的职位
    """
    logger.info(f"Recommending jobs for candidate {candidate_id}")

    # TODO: 接入实际的推荐逻辑
    # 1. 获取候选人简历和技能
    # 2. 在 Qdrant 中进行向量相似度搜索
    # 3. 返回最匹配的职位列表

    return []

# ==================== AI 生成路由 ====================
@app.post("/api/v1/ai/generate", response_model=AIGenerationResponse, tags=["AI"])
async def generate_with_ai(request: AIGenerationRequest):
    """
    使用 AI 生成内容
    可用于生成职位描述、候选人评估等
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured"
        )

    # TODO: 接入 OpenAI API
    logger.info(f"Generating AI content with prompt: {request.prompt[:50]}...")

    return AIGenerationResponse(
        content="This is a mock AI-generated response.",
        model="gpt-4",
        tokens_used=50
    )

# ==================== 聊天助手路由 ====================
@app.post("/api/v1/ai/chat", response_model=ChatResponse, tags=["AI"])
async def chat_with_assistant(request: ChatRequest):
    """
    AI 聊天助手
    为招聘经理或候选人提供智能问答服务
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OpenAI API key not configured"
        )

    session_id = request.session_id or "new_session"
    logger.info(f"Chat session: {session_id}, Messages: {len(request.messages)}")

    # TODO: 接入 OpenAI Chat API
    last_message = request.messages[-1] if request.messages else None

    return ChatResponse(
        session_id=session_id,
        message=ChatMessage(
            role="assistant",
            content="I'm here to help! How can I assist you with your recruitment needs today?"
        ),
        suggestions=[
            "Find candidates for a Python developer role",
            "Review resumes for a senior position",
            "Generate interview questions"
        ]
    )

# ==================== 异常处理器 ====================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=True
    )
