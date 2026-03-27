#!/usr/bin/env python3
"""
HigherMatch™ Test Data Seed Script
==================================

测试种子数据注入脚本。

功能:
1. 使用 Faker 生成 50 个逼真的候选人档案
2. 覆盖多种岗位: Java、Python、产品经理等
3. 覆盖多个城市: 北京、成都、上海、深圳、广州、杭州
4. 写入 PostgreSQL candidates 表
5. 调用 embedding_service 转化为 1536 维向量
6. 写入 Qdrant 向量数据库

使用方式:
    # 本地运行
    python scripts/seed_data.py

    # Docker Compose 环境
    docker compose exec candidate-service python scripts/seed_data.py

    # 带参数运行
    python scripts/seed_data.py --count 100 --batch-size 20

版本: 1.0.0
"""

import asyncio
import argparse
import hashlib
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ==================== Faker 实例 ====================
try:
    from faker import Faker
    fake = Faker("zh_CN")
except ImportError:
    logger.warning("Faker not installed, using fallback generators")
    fake = None


# ==================== 数据模型 ====================

# 技能池
SKILL_POOLS = {
    "java": [
        "Java", "Spring Boot", "Spring Cloud", "MySQL", "Redis",
        "Kafka", "Docker", "Kubernetes", "微服务", "分布式",
        "Maven", "Git", "JVM", "MyBatis", "Dubbo"
    ],
    "python": [
        "Python", "FastAPI", "Django", "Flask", "PostgreSQL",
        "MongoDB", "Redis", "Celery", "Docker", "Kubernetes",
        "机器学习", "深度学习", "TensorFlow", "PyTorch", "数据分析"
    ],
    "frontend": [
        "React", "Vue.js", "Angular", "TypeScript", "JavaScript",
        "HTML/CSS", "Webpack", "Node.js", "REST API", "GraphQL",
        "Redux", "Vite", "Tailwind CSS", "单元测试", "前端工程化"
    ],
    "product_manager": [
        "产品规划", "需求分析", "PRD 撰写", "Axure", "Figma",
        "数据分析", "用户研究", "竞品分析", "项目管理", "敏捷开发",
        "跨部门协作", "市场调研", "用户增长", "商业分析"
    ],
    "data_engineer": [
        "SQL", "Python", "Spark", "Hadoop", "Hive",
        "Kafka", "Flink", "Airflow", "数据仓库", "ETL",
        "数据建模", "Shell", "AWS/阿里云", "Docker", "Kubernetes"
    ],
    "devops": [
        "Docker", "Kubernetes", "Jenkins", "GitLab CI", "Ansible",
        "Terraform", "AWS", "阿里云", "Linux", "Shell",
        "Prometheus", "Grafana", "ELK", "监控告警", "CI/CD"
    ],
    "algorithm": [
        "Python", "C++", "算法设计", "机器学习", "深度学习",
        "NLP", "计算机视觉", "推荐系统", "搜索算法", "数据结构",
        "TensorFlow", "PyTorch", "Spark MLlib", "分布式计算"
    ],
}

# 城市列表
CITIES = [
    ("北京", "北京市", ["海淀区", "朝阳区", "西城区", "东城区", "昌平区"]),
    ("成都", "四川省", ["高新区", "天府新区", "锦江区", "武侯区"]),
    ("上海", "上海市", ["浦东新区", "徐汇区", "长宁区", "静安区"]),
    ("深圳", "广东省", ["南山区", "福田区", "宝安区", "龙华区"]),
    ("广州", "广东省", ["天河区", "海珠区", "黄埔区", "番禺区"]),
    ("杭州", "浙江省", ["西湖区", "滨江区", "余杭区", "萧山区"]),
]

# 行业列表
INDUSTRIES = [
    "互联网", "电子商务", "软件服务", "云计算", "人工智能",
    "金融科技", "游戏", "社交网络", "企业服务", "大数据",
    "物联网", "医疗健康", "教育培训", "消费电子", "新能源"
]

# 公司列表
COMPANIES = {
    "tier1": ["字节跳动", "阿里巴巴", "腾讯", "百度", "美团", "京东", "华为", "网易"],
    "tier2": ["快手", "滴滴", "拼多多", "小红书", "哔哩哔哩", "米哈游", "蚂蚁集团"],
    "tier3": ["商汤科技", "旷视科技", "依图科技", "云从科技", "寒武纪", "第四范式"],
    "other": ["各行业中大型企业", "创业公司", "外资企业", "传统企业数字化部门"]
}

# 学历列表
DEGREES = ["本科", "硕士", "博士", "MBA"]
UNIVERSITIES = [
    "清华大学", "北京大学", "浙江大学", "上海交通大学", "复旦大学",
    "南京大学", "中国科学技术大学", "哈尔滨工业大学", "西安交通大学",
    "中国人民大学", "同济大学", "北京航空航天大学", "武汉大学",
    "华中科技大学", "中山大学", "四川大学", "电子科技大学"
]

# 薪资范围 (月薪/分)
SALARY_RANGES = {
    "junior": (500000, 1500000),      # 5K-15K
    "mid": (1500000, 3000000),        # 15K-30K
    "senior": (3000000, 5000000),     # 30K-50K
    "expert": (5000000, 10000000),    # 50K-100K
}

# 工作年限配置
EXPERIENCE_RANGES = {
    "junior": (1, 3),
    "mid": (3, 5),
    "senior": (5, 8),
    "expert": (8, 15),
}


# ==================== 候选人生成器 ====================

class CandidateGenerator:
    """候选人数据生成器"""

    def __init__(self):
        self.used_phones = set()

    def generate_phone(self) -> str:
        """生成唯一手机号"""
        while True:
            phone = f"1{random.choice([3, 5, 7, 8, 9])}{random.randint(100000000, 999999999)}"
            if phone not in self.used_phones:
                self.used_phones.add(phone)
                return phone

    def generate_phone_hash(self, phone: str) -> str:
        """生成手机号哈希"""
        return hashlib.sha256(phone.encode()).hexdigest()

    def generate_experience_level(self) -> str:
        """生成经验等级"""
        return random.choice(["junior", "junior", "mid", "mid", "senior", "senior", "expert"])

    def select_skills(self, job_type: str, count: int = 8) -> list[str]:
        """选择技能"""
        base_skills = SKILL_POOLS.get(job_type, SKILL_POOLS["python"])
        # 选择核心技能
        selected = random.sample(base_skills, min(count, len(base_skills)))
        # 添加一些通识技能
        common_skills = ["团队协作", "沟通能力", "问题解决", "学习能力"]
        if random.random() > 0.5:
            selected.extend(random.sample(common_skills, 1))
        return list(set(selected))

    def generate_work_history(self, years_exp: int, job_type: str) -> list[dict]:
        """生成工作经历"""
        history = []
        current_year = datetime.now().year
        remaining_years = years_exp

        tier_choice = random.choices(
            ["tier1", "tier2", "tier3", "other"],
            weights=[0.2, 0.3, 0.2, 0.3]
        )[0]
        company_pool = COMPANIES[tier_choice]

        # 职位级别映射
        level_titles = {
            "junior": ["初级工程师", "助理工程师", "工程师"],
            "mid": ["工程师", "高级工程师", "资深工程师"],
            "senior": ["高级工程师", "资深工程师", "技术专家", "Tech Lead"],
            "expert": ["技术专家", "架构师", "技术总监", "VP"],
        }

        for i in range(min(3, max(1, (years_exp + 2) // 3))):
            if remaining_years <= 0:
                break

            period = min(3, remaining_years)
            end_year = current_year - i * 3 if i > 0 else current_year
            start_year = end_year - period

            title = random.choice(level_titles.get(job_type, level_titles["mid"]))

            history.append({
                "company": random.choice(company_pool),
                "title": title,
                "start_date": f"{start_year}-{random.randint(1, 12):02d}",
                "end_date": None if i == 0 else f"{end_year - 1}-{random.randint(1, 12):02d}",
                "description": f"负责{job_type}相关开发工作，参与核心系统建设",
            })

            remaining_years -= period

        return history

    def generate_education(self) -> list[dict]:
        """生成教育经历"""
        return [{
            "school": random.choice(UNIVERSITIES),
            "degree": random.choice(DEGREES[:2]),  # 主要是本科和硕士
            "major": random.choice(["计算机科学与技术", "软件工程", "电子信息工程", "数学", "统计学"]),
            "start_date": str(random.randint(2010, 2018)),
            "end_date": str(random.randint(2014, 2022)),
        }]

    def generate_candidate(self, job_type: str) -> dict:
        """生成单个候选人数据"""
        # 基本信息
        name = fake.name() if fake else f"用户{random.randint(10000, 99999)}"
        phone = self.generate_phone()
        email = f"{name.lower()}{random.randint(1, 99)}@example.com"

        # 地理位置
        city, province, districts = random.choice(CITIES)
        district = random.choice(districts)

        # 经验等级和年限
        level = self.generate_experience_level()
        years_exp = random.randint(*EXPERIENCE_RANGES[level])

        # 技能
        skills = self.select_skills(job_type, count=random.randint(6, 12))

        # 工作经历
        work_history = self.generate_work_history(years_exp, job_type)

        # 教育经历
        education = self.generate_education()

        # 薪资期望
        salary_range = SALARY_RANGES.get(level, SALARY_RANGES["mid"])
        expected_salary_min = random.randint(*salary_range)
        expected_salary_max = expected_salary_min + random.randint(50000, 200000)

        # 求职状态
        job_status = random.choice(["active", "active", "passive", "urgent"])

        # 画像数据
        profile = {
            "skills": skills,
            "work_history": work_history,
            "education": education,
            "certifications": random.sample(["PMP", "AWS认证", "CKA", "OCP", "软考高级"], k=random.randint(0, 2)),
            "summary": fake.text(max_nb_chars=200) if fake else "专业工程师",
        }

        return {
            "phone_hash": self.generate_phone_hash(phone),
            "email": email,
            "name": name,
            "gender": random.choice(["男", "女"]),
            "birth_date": datetime.now().date() - timedelta(days=random.randint(7300, 12000)),
            "current_province": province,
            "current_city": city,
            "current_district": district,
            "job_search_status": job_status,
            "profile": profile,
            "skills": skills,
            "work_history": work_history,
            "education": education,
            "total_years_exp": years_exp,
            "expected_salary_min": expected_salary_min,
            "expected_salary_max": expected_salary_max,
            "preferred_job_titles": [f"{job_type}工程师", f"高级{job_type}工程师"],
            "preferred_locations": [city, random.choice([c[0] for c in CITIES if c[0] != city])],
            "preferred_industries": random.sample(INDUSTRIES, k=2),
            "profile_completeness": random.uniform(0.7, 1.0),
            "verification_score": random.uniform(0.5, 0.95),
            "is_active": True,
        }


# ==================== 数据库操作 ====================

async def init_database():
    """初始化数据库连接"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import async_sessionmaker

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://highermatch:highermatch@localhost:5432/highermatch_dev"
    )

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    return engine, async_session


async def create_candidate_in_db(async_session, candidate_data: dict) -> str:
    """
    将候选人数据写入 PostgreSQL

    Args:
        async_session: 数据库会话工厂
        candidate_data: 候选人数据

    Returns:
        候选人 ID (UUID 字符串)
    """
    import uuid
    from sqlalchemy import text
    from datetime import datetime

    candidate_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # 构建 SQL 插入语句
    insert_sql = text("""
        INSERT INTO candidates (
            id, phone_hash, email, name, gender, birth_date,
            current_province, current_city, current_district,
            job_search_status, profile, skills, work_history,
            education, total_years_exp, expected_salary_min,
            expected_salary_max, preferred_job_titles,
            preferred_locations, preferred_industries,
            profile_completeness, verification_score,
            is_active, embedding_vector_id, created_at, updated_at
        ) VALUES (
            :id, :phone_hash, :email, :name, :gender, :birth_date,
            :current_province, :current_city, :current_district,
            :job_search_status, :profile, :skills, :work_history,
            :education, :total_years_exp, :expected_salary_min,
            :expected_salary_max, :preferred_job_titles,
            :preferred_locations, :preferred_industries,
            :profile_completeness, :verification_score,
            :is_active, :embedding_vector_id, :created_at, :updated_at
        )
    """)

    async with async_session() as session:
        await session.execute(insert_sql, {
            "id": candidate_id,
            "phone_hash": candidate_data["phone_hash"],
            "email": candidate_data["email"],
            "name": candidate_data["name"],
            "gender": candidate_data["gender"],
            "birth_date": candidate_data["birth_date"],
            "current_province": candidate_data["current_province"],
            "current_city": candidate_data["current_city"],
            "current_district": candidate_data["current_district"],
            "job_search_status": candidate_data["job_search_status"],
            "profile": json.dumps(candidate_data["profile"]),
            "skills": candidate_data["skills"],
            "work_history": candidate_data["work_history"],
            "education": candidate_data["education"],
            "total_years_exp": candidate_data["total_years_exp"],
            "expected_salary_min": candidate_data["expected_salary_min"],
            "expected_salary_max": candidate_data["expected_salary_max"],
            "preferred_job_titles": candidate_data["preferred_job_titles"],
            "preferred_locations": candidate_data["preferred_locations"],
            "preferred_industries": candidate_data["preferred_industries"],
            "profile_completeness": candidate_data["profile_completeness"],
            "verification_score": candidate_data["verification_score"],
            "is_active": candidate_data["is_active"],
            "embedding_vector_id": None,
            "created_at": now,
            "updated_at": now,
        })
        await session.commit()

    return candidate_id


# ==================== 向量化和 VDB 操作 ====================

async def generate_embedding(text: str) -> list[float]:
    """
    生成文本的 embedding 向量

    Args:
        text: 输入文本

    Returns:
        1536 维向量列表
    """
    try:
        # 尝试使用 OpenAI API
        import httpx
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "model": "text-embedding-ada-002",
                }
            )
            response.raise_for_status()
            result = response.json()
            return result["data"][0]["embedding"]

    except Exception as e:
        logger.warning(f"OpenAI API failed, using mock embedding: {e}")
        # 返回模拟向量
        import random
        random.seed(hash(text) % (2**32))
        vector = [random.random() for _ in range(1536)]
        # 归一化
        magnitude = sum(v * v for v in vector) ** 0.5
        if magnitude > 0:
            vector = [v / magnitude for v in vector]
        return vector


def build_profile_text(candidate: dict) -> str:
    """构建候选人档案文本用于向量化"""
    parts = []

    # 姓名
    if candidate.get("name"):
        parts.append(f"姓名: {candidate['name']}")

    # 技能
    skills = candidate.get("skills", [])
    if skills:
        parts.append(f"技能: {', '.join(skills)}")

    # 工作年限
    years = candidate.get("total_years_exp", 0)
    parts.append(f"工作年限: {years}年")

    # 工作经历
    work_history = candidate.get("work_history", [])
    for work in work_history[:2]:
        company = work.get("company", "")
        title = work.get("title", "")
        desc = work.get("description", "")
        if company or title:
            parts.append(f"经历: {company} {title} {desc}")

    # 期望职位
    titles = candidate.get("preferred_job_titles", [])
    if titles:
        parts.append(f"期望职位: {', '.join(titles)}")

    # 期望地点
    locations = candidate.get("preferred_locations", [])
    if locations:
        parts.append(f"期望地点: {', '.join(locations)}")

    # 期望行业
    industries = candidate.get("preferred_industries", [])
    if industries:
        parts.append(f"期望行业: {', '.join(industries)}")

    return " | ".join(parts)


async def upsert_to_vdb(candidate_id: str, vector: list[float], payload: dict) -> bool:
    """
    将候选人向量写入 Qdrant

    Args:
        candidate_id: 候选人 ID
        vector: 1536 维向量
        payload: 候选人元数据

    Returns:
        是否成功
    """
    try:
        import httpx

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        collection = os.getenv("QDRANT_COLLECTION", "candidates")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{qdrant_url}/collections/{collection}/points",
                json={
                    "points": [{
                        "id": str(candidate_id),
                        "vector": vector,
                        "payload": {
                            "candidate_id": str(candidate_id),
                            **payload
                        }
                    }]
                }
            )
            response.raise_for_status()
            return True

    except Exception as e:
        logger.error(f"Failed to upsert to VDB: {e}")
        return False


# ==================== 主流程 ====================

async def seed_candidates(
    count: int = 50,
    batch_size: int = 10,
    job_types: Optional[list[str]] = None,
) -> dict:
    """
    主种子数据注入流程

    Args:
        count: 生成候选人数量
        batch_size: 批量提交大小
        job_types: 岗位类型列表

    Returns:
        统计信息
    """
    import time

    logger.info(f"Starting seed data generation: count={count}, batch_size={batch_size}")

    # 初始化
    engine, async_session = await init_database()
    generator = CandidateGenerator()

    # 岗位类型分布
    if job_types is None:
        job_types = list(SKILL_POOLS.keys())

    # 生成候选人数据
    candidates_data = []
    for i in range(count):
        job_type = random.choice(job_types)
        candidate = generator.generate_candidate(job_type)
        candidates_data.append(candidate)
        logger.debug(f"Generated candidate {i+1}/{count}: {candidate['name']} ({job_type})")

    # 批量处理
    stats = {
        "total": count,
        "db_success": 0,
        "db_failed": 0,
        "vdb_success": 0,
        "vdb_failed": 0,
        "errors": [],
    }

    for i in range(0, len(candidates_data), batch_size):
        batch = candidates_data[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(candidates_data) + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} candidates)")

        for candidate in batch:
            try:
                # 1. 写入数据库
                candidate_id = await create_candidate_in_db(async_session, candidate)
                stats["db_success"] += 1
                logger.info(f"  [DB] Created candidate {candidate['name']} (ID: {candidate_id})")

                # 2. 生成 embedding
                profile_text = build_profile_text(candidate)
                vector = await generate_embedding(profile_text)

                # 3. 写入 VDB
                vdb_payload = {
                    "name": candidate["name"],
                    "skills": candidate["skills"],
                    "total_years_exp": candidate["total_years_exp"],
                    "current_city": candidate["current_city"],
                    "preferred_locations": candidate["preferred_locations"],
                    "preferred_industries": candidate["preferred_industries"],
                    "expected_salary_min": candidate["expected_salary_min"],
                    "expected_salary_max": candidate["expected_salary_max"],
                    "job_search_status": candidate["job_search_status"],
                    "work_history": candidate["work_history"],
                    "verification_score": candidate["verification_score"],
                }

                if await upsert_to_vdb(candidate_id, vector, vdb_payload):
                    stats["vdb_success"] += 1
                    logger.info(f"  [VDB] Upserted vector for {candidate['name']}")
                else:
                    stats["vdb_failed"] += 1
                    stats["errors"].append(f"VDB failed for {candidate['name']}")

                # 限流
                await asyncio.sleep(0.1)

            except Exception as e:
                stats["db_failed"] += 1
                stats["errors"].append(f"DB failed for {candidate['name']}: {str(e)}")
                logger.error(f"  [ERROR] {candidate['name']}: {e}")

        logger.info(f"Batch {batch_num}/{total_batches} completed")

    # 清理
    await engine.dispose()

    # 打印统计
    logger.info("=" * 50)
    logger.info("Seed Data Generation Complete!")
    logger.info(f"  Total: {stats['total']}")
    logger.info(f"  DB Success: {stats['db_success']}")
    logger.info(f"  DB Failed: {stats['db_failed']}")
    logger.info(f"  VDB Success: {stats['vdb_success']}")
    logger.info(f"  VDB Failed: {stats['vdb_failed']}")
    if stats["errors"]:
        logger.info(f"  Errors: {len(stats['errors'])}")
        for err in stats["errors"][:5]:
            logger.info(f"    - {err}")
    logger.info("=" * 50)

    return stats


async def create_test_job() -> dict:
    """
    创建一个测试岗位用于 E2E 测试

    Returns:
        岗位数据
    """
    import uuid
    from sqlalchemy import text
    from datetime import datetime

    _, async_session = await init_database()

    # 生成雇主 ID
    employer_id = str(uuid.uuid4())

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

    now = datetime.utcnow()

    async with async_session() as session:
        await session.execute(employer_sql, {
            "id": employer_id,
            "company_name": "HigherMatch Tech",
            "industry": "人工智能",
            "company_size": "201-500",
            "contact_name": "张三",
            "contact_email": "hr@highermatch.com",
            "contact_phone": "13800138000",
            "kyc_status": "approved",
            "is_verified": True,
            "credit_balance": 10000000,
            "created_at": now,
            "updated_at": now,
        })

        # 创建测试岗位
        job_id = str(uuid.uuid4())
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

        await session.execute(job_sql, {
            "id": job_id,
            "employer_id": employer_id,
            "job_title": "Python 后端工程师",
            "job_category": "技术",
            "job_tags": ["Python", "FastAPI", "高薪", "弹性工作"],
            "requirement": json.dumps({
                "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
                "core_skills": ["Python", "FastAPI"],
                "years_exp_min": 3,
                "years_exp_max": 8,
                "industries": ["互联网", "软件服务", "人工智能"],
                "education": "本科及以上",
            }),
            "work_city": "北京",
            "work_province": "北京市",
            "work_location_type": "onsite",
            "salary_min": 2500000,
            "salary_max": 4500000,
            "employment_type": "full_time",
            "status": "published",
            "commission_rate": 0.15,
            "is_urgent": True,
            "published_at": now,
            "created_at": now,
            "updated_at": now,
        })

        await session.commit()

    return {
        "job_id": job_id,
        "employer_id": employer_id,
        "job_data": {
            "id": job_id,
            "employer_id": employer_id,
            "job_title": "Python 后端工程师",
            "company_name": "HigherMatch Tech",
            "requirement": {
                "skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker"],
                "core_skills": ["Python", "FastAPI"],
                "years_exp_min": 3,
                "years_exp_max": 8,
                "industries": ["互联网", "软件服务", "人工智能"],
            },
            "salary_min": 2500000,
            "salary_max": 4500000,
        }
    }


# ==================== CLI 入口 ====================

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="HigherMatch™ 测试数据种子注入脚本"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=50,
        help="生成候选人数量 (默认: 50)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=10,
        help="批量提交大小 (默认: 10)"
    )
    parser.add_argument(
        "--job-types", "-j",
        nargs="+",
        choices=list(SKILL_POOLS.keys()),
        default=None,
        help="岗位类型"
    )
    parser.add_argument(
        "--create-job",
        action="store_true",
        help="同时创建测试岗位"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )

    return parser.parse_args()


async def main():
    """主入口"""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("HigherMatch™ Seed Data Script")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Database: {os.getenv('DATABASE_URL', 'postgresql://...')}")
    logger.info(f"Qdrant: {os.getenv('QDRANT_URL', 'http://localhost:6333')}")
    logger.info("-" * 50)

    # 生成种子数据
    stats = await seed_candidates(
        count=args.count,
        batch_size=args.batch_size,
        job_types=args.job_types,
    )

    # 可选：创建测试岗位
    if args.create_job:
        logger.info("-" * 50)
        logger.info("Creating test job for E2E testing...")
        job_info = await create_test_job()
        logger.info(f"Test job created: {job_info['job_id']}")
        logger.info(f"Employer: {job_info['employer_id']}")

        # 保存到文件供后续使用
        output_file = "/tmp/highermatch_test_job.json"
        with open(output_file, "w") as f:
            json.dump(job_info, f, indent=2, default=str)
        logger.info(f"Job info saved to: {output_file}")

    return stats


if __name__ == "__main__":
    asyncio.run(main())
