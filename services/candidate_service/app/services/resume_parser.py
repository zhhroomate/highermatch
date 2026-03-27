"""
HigherMatch™ Candidate Service - Resume Parser
===============================================

简历解析模块，支持 PDF 文本提取和 LLM 结构化解析。

功能:
1. 使用 PyMuPDF (fitz) 提取 PDF 文本
2. 调用 LLM 将文本解析为结构化 JSON
3. 支持缓存解析结果

版本: 1.0.0
"""

import hashlib
import io
import logging
from typing import Optional
from datetime import datetime

import fitz  # PyMuPDF
from pydantic import BaseModel, Field

from shared.llm_client import ChatMessage, get_llm_client, LLMError

# ==================== 日志配置 ====================
logger = logging.getLogger(__name__)


# ==================== 解析结果模型 ====================
class ParsedEducation(BaseModel):
    """教育经历"""
    school: str = Field(description="学校名称")
    degree: Optional[str] = Field(default=None, description="学位")
    major: Optional[str] = Field(default=None, description="专业")
    start_date: Optional[str] = Field(default=None, description="开始时间")
    end_date: Optional[str] = Field(default=None, description="结束时间")
    gpa: Optional[str] = Field(default=None, description="GPA")


class ParsedWorkHistory(BaseModel):
    """工作经历"""
    company: str = Field(description="公司名称")
    title: str = Field(description="职位名称")
    start_date: Optional[str] = Field(default=None, description="开始时间")
    end_date: Optional[str] = Field(default=None, description="结束时间 (空表示至今)")
    description: Optional[str] = Field(default=None, description="工作描述")
    achievements: Optional[list[str]] = Field(default=None, description="主要成就")


class ParsedResume(BaseModel):
    """解析后的简历数据"""
    education: list[ParsedEducation] = Field(default_factory=list, description="教育经历")
    work_history: list[ParsedWorkHistory] = Field(default_factory=list, description="工作经历")
    skills: list[str] = Field(default_factory=list, description="技能列表")
    total_years_exp: int = Field(default=0, description="总工作年限")
    name: Optional[str] = Field(default=None, description="姓名")
    email: Optional[str] = Field(default=None, description="邮箱")
    phone: Optional[str] = Field(default=None, description="电话")
    summary: Optional[str] = Field(default=None, description="个人简介")
    certifications: Optional[list[str]] = Field(default=None, description="证书")


class ResumeParseResult(BaseModel):
    """简历解析结果 (包含元数据)"""
    success: bool = Field(description="解析是否成功")
    candidate_id: int = Field(description="候选人 ID")
    resume_id: str = Field(description="简历 ID (UUID)")
    parsed_data: Optional[ParsedResume] = Field(default=None, description="解析数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    raw_text_length: int = Field(default=0, description="原始文本长度")
    parsed_at: datetime = Field(default_factory=datetime.utcnow, description="解析时间")
    from_cache: bool = Field(default=False, description="是否来自缓存")


# ==================== 系统提示词 ====================
RESUME_PARSE_SYSTEM_PROMPT = """你是一个专业的简历解析 AI。请从简历文本中提取结构化信息。

要求:
1. 只返回 JSON 格式，不要包含任何其他文字
2. 所有字段使用中文或英文都可以
3. 教育经历按时间倒序排列
4. 工作经历按时间倒序排列
5. 技能列表只返回技术技能和语言技能
6. 工作年限需要根据工作经历计算总年数

输出格式:
{
    "name": "姓名",
    "email": "邮箱",
    "phone": "电话",
    "summary": "个人简介",
    "education": [
        {
            "school": "学校名称",
            "degree": "学位",
            "major": "专业",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM 或至今"
        }
    ],
    "work_history": [
        {
            "company": "公司名称",
            "title": "职位名称",
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM 或至今",
            "description": "工作描述",
            "achievements": ["成就1", "成就2"]
        }
    ],
    "skills": ["技能1", "技能2"],
    "total_years_exp": 数字,
    "certifications": ["证书1", "证书2"]
}
"""


# ==================== 简历解析器 ====================
class ResumeParser:
    """
    简历解析器

    负责从 PDF 文件中提取文本并调用 LLM 进行结构化解析。
    """

    def __init__(
        self,
        max_file_size_mb: int = 10,
        supported_formats: tuple = (".pdf",),
    ):
        """
        初始化简历解析器

        Args:
            max_file_size_mb: 最大文件大小 (MB)
            supported_formats: 支持的文件格式
        """
        self.max_file_size = max_file_size_mb * 1024 * 1024  # 转换为字节
        self.supported_formats = supported_formats
        self._llm_client = get_llm_client()

    def _validate_file(self, content: bytes, filename: str) -> None:
        """
        验证文件

        Args:
            content: 文件内容
            filename: 文件名

        Raises:
            ValueError: 文件验证失败
        """
        # 检查文件大小
        if len(content) > self.max_file_size:
            raise ValueError(
                f"文件大小超过限制 ({self.max_file_size // (1024*1024)}MB)"
            )

        # 检查文件格式
        ext = filename.lower().split('.')[-1]
        if f'.{ext}' not in self.supported_formats:
            raise ValueError(
                f"不支持的文件格式: .{ext}，仅支持: {', '.join(self.supported_formats)}"
            )

    def extract_text_from_pdf(self, content: bytes) -> str:
        """
        从 PDF 中提取文本

        Args:
            content: PDF 文件内容 (bytes)

        Returns:
            提取的文本内容
        """
        text_parts = []

        try:
            # 使用 PyMuPDF 打开 PDF
            doc = fitz.open(stream=content, filetype="pdf")

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # 清理文本
                text = text.strip()
                if text:
                    text_parts.append(f"[第 {page_num + 1} 页]\n{text}")

            doc.close()

        except Exception as e:
            logger.error(f"PDF 解析错误: {e}")
            raise ValueError(f"无法解析 PDF 文件: {str(e)}")

        return "\n\n".join(text_parts)

    def _generate_cache_key(text: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(text.encode()).hexdigest()[:32]

    async def parse_resume(
        self,
        content: bytes,
        filename: str,
        candidate_id: int,
        resume_id: str,
    ) -> ResumeParseResult:
        """
        解析简历

        Args:
            content: 文件内容
            filename: 文件名
            candidate_id: 候选人 ID
            resume_id: 简历 ID

        Returns:
            解析结果
        """
        # 验证文件
        self._validate_file(content, filename)

        # 提取文本
        raw_text = self.extract_text_from_pdf(content)
        text_length = len(raw_text)

        if not raw_text or text_length < 50:
            return ResumeParseResult(
                success=False,
                candidate_id=candidate_id,
                resume_id=resume_id,
                error="无法从简历中提取足够的文本内容",
                raw_text_length=text_length,
            )

        # 调用 LLM 解析
        try:
            parsed_data = await self._parse_with_llm(raw_text)

            return ResumeParseResult(
                success=True,
                candidate_id=candidate_id,
                resume_id=resume_id,
                parsed_data=parsed_data,
                raw_text_length=text_length,
            )

        except LLMError as e:
            logger.error(f"LLM 解析失败: {e}")
            return ResumeParseResult(
                success=False,
                candidate_id=candidate_id,
                resume_id=resume_id,
                error=f"AI 解析失败: {str(e)}",
                raw_text_length=text_length,
            )

        except Exception as e:
            logger.error(f"简历解析异常: {e}")
            return ResumeParseResult(
                success=False,
                candidate_id=candidate_id,
                resume_id=resume_id,
                error=f"解析失败: {str(e)}",
                raw_text_length=text_length,
            )

    async def _parse_with_llm(self, text: str) -> ParsedResume:
        """
        使用 LLM 解析文本

        Args:
            text: 原始文本

        Returns:
            解析后的简历数据
        """
        messages = [
            ChatMessage(role="system", content=RESUME_PARSE_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"请解析以下简历文本:\n\n{text[:15000]}"),
        ]

        result = await self._llm_client.parse_json(messages)
        return ParsedResume(**result)

    async def parse_text_direct(
        self,
        text: str,
        candidate_id: int,
        resume_id: str,
    ) -> ResumeParseResult:
        """
        直接解析文本 (用于测试或已有文本的情况)

        Args:
            text: 原始文本
            candidate_id: 候选人 ID
            resume_id: 简历 ID

        Returns:
            解析结果
        """
        text_length = len(text)

        if not text or text_length < 50:
            return ResumeParseResult(
                success=False,
                candidate_id=candidate_id,
                resume_id=resume_id,
                error="文本内容不足",
                raw_text_length=text_length,
            )

        try:
            parsed_data = await self._parse_with_llm(text)

            return ResumeParseResult(
                success=True,
                candidate_id=candidate_id,
                resume_id=resume_id,
                parsed_data=parsed_data,
                raw_text_length=text_length,
            )

        except LLMError as e:
            logger.error(f"LLM 解析失败: {e}")
            return ResumeParseResult(
                success=False,
                candidate_id=candidate_id,
                resume_id=resume_id,
                error=f"AI 解析失败: {str(e)}",
                raw_text_length=text_length,
            )

        except Exception as e:
            logger.error(f"简历解析异常: {e}")
            return ResumeParseResult(
                success=False,
                candidate_id=candidate_id,
                resume_id=resume_id,
                error=f"解析失败: {str(e)}",
                raw_text_length=text_length,
            )


# ==================== 单例 ====================
_resume_parser: Optional[ResumeParser] = None


def get_resume_parser() -> ResumeParser:
    """获取简历解析器实例"""
    global _resume_parser
    if _resume_parser is None:
        _resume_parser = ResumeParser()
    return _resume_parser


# ==================== 导出 ====================
__all__ = [
    "ResumeParser",
    "ParsedResume",
    "ParsedEducation",
    "ParsedWorkHistory",
    "ResumeParseResult",
    "get_resume_parser",
]
