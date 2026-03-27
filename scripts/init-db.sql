-- ============================================================================
-- HigherMatch™ AI 招聘平台 - PostgreSQL 数据库初始化脚本
-- 版本: 2.0.0 (PRD 核心数据模型)
-- ============================================================================
-- 使用说明:
-- 1. 确保 PostgreSQL 15+ 已安装
-- 2. 创建数据库: CREATE DATABASE highermatch_dev;
-- 3. 执行脚本: psql -U postgres -d highermatch_dev -f init-db.sql
-- ============================================================================

-- ============================================================================
-- 第一部分: 扩展和配置
-- ============================================================================

-- 启用 UUID 生成扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 启用 JSONB 索引扩展
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 设置时区
SET TimeZone = 'Asia/Shanghai';

-- ============================================================================
-- 第二部分: 枚举类型定义
-- ============================================================================

-- KYC 状态枚举
DO $$ BEGIN
    CREATE TYPE kyc_status AS ENUM ('pending', 'in_review', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 职位发布状态枚举
DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('draft', 'published', 'closed', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 求职状态枚举
DO $$ BEGIN
    CREATE TYPE job_search_status AS ENUM ('not_looking', 'passive', 'active', 'urgent');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 匹配管道阶段枚举
DO $$ BEGIN
    CREATE TYPE pipeline_stage AS ENUM (
        'ai_recommended',
        'employer_reviewed',
        'interview_scheduled',
        'interview_completed',
        'offer_sent',
        'offer_accepted',
        'onboarded',
        'rejected',
        'withdrawn'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 发票状态枚举
DO $$ BEGIN
    CREATE TYPE invoice_status AS ENUM ('pending', 'paid', 'overdue', 'cancelled', 'refunded');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 担保状态枚举
DO $$ BEGIN
    CREATE TYPE guarantee_status AS ENUM ('active', 'expired', 'claimed', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 支付方式枚举
DO $$ BEGIN
    CREATE TYPE payment_method AS ENUM ('bank_transfer', 'credit_card', 'alipay', 'wechat_pay', 'corporate_account');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- 第三部分: 核心数据表
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 表 1: employers (雇主/企业表)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employers (
    -- 主键: UUID 类型，使用 gen_random_uuid() 生成
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 企业基本信息
    company_name VARCHAR(300) NOT NULL,
    industry VARCHAR(100),
    company_size VARCHAR(50),  -- e.g., '1-50', '51-200', '201-500', '501-1000', '1000+'
    company_description TEXT,
    company_website VARCHAR(500),
    company_logo_url TEXT,

    -- KYC 认证状态
    kyc_status kyc_status NOT NULL DEFAULT 'pending',
    kyc_submitted_at TIMESTAMPTZ,
    kyc_verified_at TIMESTAMPTZ,
    kyc_rejection_reason TEXT,

    -- 联系信息
    contact_name VARCHAR(200) NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20) NOT NULL,
    contact_title VARCHAR(100),

    -- 财务信息
    credit_balance BIGINT NOT NULL DEFAULT 0,  -- 账户余额，单位：分
    total_spent BIGINT NOT NULL DEFAULT 0,     -- 累计消费
    pending_payment BIGINT NOT NULL DEFAULT 0,  -- 待结算金额

    -- 地址信息
    province VARCHAR(50),
    city VARCHAR(50),
    district VARCHAR(50),
    address_detail TEXT,
    business_license_url TEXT,

    -- 审核信息
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 约束
    CONSTRAINT employers_credit_balance_check CHECK (credit_balance >= 0),
    CONSTRAINT employers_total_spent_check CHECK (total_spent >= 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_employers_company_name ON employers(company_name);
CREATE INDEX IF NOT EXISTS idx_employers_industry ON employers(industry);
CREATE INDEX IF NOT EXISTS idx_employers_kyc_status ON employers(kyc_status);
CREATE INDEX IF NOT EXISTS idx_employers_contact_phone ON employers(contact_phone);
CREATE INDEX IF NOT EXISTS idx_employers_created_at ON employers(created_at DESC);

-- ---------------------------------------------------------------------------
-- 表 2: candidates (候选人表)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS candidates (
    -- 主键: UUID 类型
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 联系方式 (phone_hash 用于唯一索引和登录)
    phone_hash VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(255),
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,

    -- 基本信息
    name VARCHAR(200),
    avatar_url TEXT,
    gender VARCHAR(10),
    birth_date DATE,
    age INTEGER,

    -- 地理位置
    current_province VARCHAR(50),
    current_city VARCHAR(50),
    current_district VARCHAR(50),

    -- 求职状态
    job_search_status job_search_status NOT NULL DEFAULT 'passive',

    -- 画像数据 (JSONB 存储灵活结构)
    profile JSONB NOT NULL DEFAULT '{}',
    /* profile 结构示例:
    {
        "education": [
            {"school": "MIT", "degree": "Master", "major": "CS", "graduation_year": 2020}
        ],
        "work_experience": [
            {"company": "Google", "title": "Software Engineer", "duration": "2020-2023", "description": "..."}
        ],
        "skills": ["Python", "JavaScript", "PostgreSQL"],
        "certifications": ["AWS Solutions Architect"],
        "languages": ["English: Fluent", "Chinese: Native"]
    }
    */

    -- 向量嵌入 ID (关联 Qdrant)
    embedding_vector_id VARCHAR(100),

    -- 认证信息
    verification_score FLOAT,  -- 0.0 - 1.0

    -- 简历信息
    resume_id UUID,
    resume_url TEXT,
    resume_parsed_at TIMESTAMPTZ,

    -- 完成度
    profile_completeness FLOAT NOT NULL DEFAULT 0.0,  -- 0.0 - 1.0

    -- 期望工作
    expected_salary_min INTEGER,
    expected_salary_max INTEGER,
    preferred_job_titles TEXT[],
    preferred_locations TEXT[],
    preferred_industries TEXT[],

    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 约束
    CONSTRAINT candidates_age_check CHECK (age IS NULL OR (age >= 18 AND age <= 100)),
    CONSTRAINT candidates_profile_completeness_check CHECK (profile_completeness >= 0.0 AND profile_completeness <= 1.0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_candidates_phone_hash ON candidates(phone_hash);
CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);
CREATE INDEX IF NOT EXISTS idx_candidates_job_search_status ON candidates(job_search_status);
CREATE INDEX IF NOT EXISTS idx_candidates_profile_completeness ON candidates(profile_completeness DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidates_embedding ON candidates(embedding_vector_id);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_candidates_profile_gin ON candidates USING GIN (profile jsonb_path_ops);

-- ---------------------------------------------------------------------------
-- 表 3: jobs (职位表)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    -- 主键: UUID 类型
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 雇主外键
    employer_id UUID NOT NULL REFERENCES employers(id) ON DELETE RESTRICT,

    -- 职位基本信息
    job_title VARCHAR(300) NOT NULL,
    job_category VARCHAR(100),
    job_tags TEXT[],  -- e.g., ['远程', '高薪', '急招']

    -- 职位描述 (JSONB 结构化存储)
    requirement JSONB NOT NULL DEFAULT '{}',
    /* requirement 结构示例:
    {
        "education": "本科以上",
        "experience_years": "3-5年",
        "languages": ["中文", "英语"],
        "skills_required": ["Python", "Django", "PostgreSQL"],
        "soft_skills": ["沟通能力", "团队协作"],
        "certifications_preferred": ["PMP", "AWS"]
    }
    */

    -- 职位详情 HTML
    jd_html TEXT,  -- 富文本职位描述

    -- 职位类型
    employment_type VARCHAR(50),  -- 'full_time', 'part_time', 'contract', 'internship'

    -- 工作地点
    work_location_type VARCHAR(50),  -- 'onsite', 'remote', 'hybrid'
    work_province VARCHAR(50),
    work_city VARCHAR(50),
    work_district VARCHAR(50),
    work_address_detail TEXT,

    -- 薪资范围 (单位: 月薪，分)
    salary_min INTEGER,
    salary_max INTEGER,
    salary_negotiable BOOLEAN DEFAULT FALSE,
    salary_show_type VARCHAR(20),  -- 'exact', 'range', 'negotiable', 'hidden'

    -- 佣金配置
    commission_rate FLOAT NOT NULL DEFAULT 0.10,  -- 佣金率，默认 10%
    commission_fixed_amount BIGINT,  -- 固定佣金金额

    -- 紧急标识
    is_urgent BOOLEAN NOT NULL DEFAULT FALSE,
    urgent_expires_at TIMESTAMPTZ,

    -- 发布状态
    status job_status NOT NULL DEFAULT 'draft',

    -- 投递限制
    max_applications INTEGER,  -- 最大接收申请数
    current_applications INTEGER NOT NULL DEFAULT 0,

    -- 查看统计
    view_count INTEGER NOT NULL DEFAULT 0,
    apply_count INTEGER NOT NULL DEFAULT 0,

    -- 发布时间
    published_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    -- 软删除
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 约束
    CONSTRAINT jobs_salary_check CHECK (
        (salary_min IS NULL OR salary_max IS NULL) OR
        (salary_min <= salary_max)
    ),
    CONSTRAINT jobs_commission_rate_check CHECK (
        commission_rate >= 0.0 AND commission_rate <= 1.0
    )
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_jobs_employer_id ON jobs(employer_id);
CREATE INDEX IF NOT EXISTS idx_jobs_job_title ON jobs(job_title);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_is_urgent ON jobs(is_urgent) WHERE is_urgent = TRUE;
CREATE INDEX IF NOT EXISTS idx_jobs_published_at ON jobs(published_at DESC) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_work_city ON jobs(work_city);

-- GIN 索引用于 JSONB 查询和数组查询
CREATE INDEX IF NOT EXISTS idx_jobs_requirement ON jobs USING GIN (requirement jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_jobs_tags ON jobs USING GIN (job_tags);

-- ---------------------------------------------------------------------------
-- 表 4: match_results (匹配结果表)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS match_results (
    -- 主键: UUID 类型
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 外键
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    employer_id UUID NOT NULL REFERENCES employers(id) ON DELETE CASCADE,

    -- 匹配管道阶段
    pipeline_stage pipeline_stage NOT NULL DEFAULT 'ai_recommended',

    -- 总体匹配分数
    overall_score FLOAT NOT NULL,  -- 0.0 - 1.0

    -- 分数细分 (JSONB)
    score_breakdown JSONB NOT NULL DEFAULT '{}',
    /* score_breakdown 结构示例:
    {
        "skill_match": 0.85,
        "experience_match": 0.75,
        "education_match": 0.90,
        "location_match": 1.0,
        "salary_match": 0.80,
        "culture_match": 0.70,
        "career_growth_match": 0.65
    }
    */

    -- 匹配原因 (数组)
    match_reasons TEXT[],
    /* match_reasons 示例:
    ['3年Python开发经验', '985高校计算机专业', '薪资期望匹配']
    */

    -- 拒绝原因
    rejection_reasons TEXT[],

    -- AI 生成的推荐理由
    ai_recommendation TEXT,

    -- 薪资信息
    offer_amount INTEGER,  -- Offer 金额 (月薪，分)
    last_salary INTEGER,    -- 上一份工作薪资

    -- 入职信息
    onboard_date DATE,
    probation_end_date DATE,

    -- 时间线记录 (JSONB)
    timeline JSONB NOT NULL DEFAULT '[]',
    /* timeline 结构示例:
    [
        {"stage": "ai_recommended", "at": "2024-01-15T10:00:00Z", "by": "system"},
        {"stage": "employer_reviewed", "at": "2024-01-16T14:30:00Z", "by": "user_uuid", "notes": "..."}
    ]
    */

    -- 备注
    internal_notes TEXT,

    -- 软删除
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 约束
    CONSTRAINT match_results_score_check CHECK (overall_score >= 0.0 AND overall_score <= 1.0),

    -- 唯一约束: 每个候选人每个职位只能有一条匹配记录
    CONSTRAINT match_results_unique_job_candidate UNIQUE (job_id, candidate_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_match_results_job_id ON match_results(job_id);
CREATE INDEX IF NOT EXISTS idx_match_results_candidate_id ON match_results(candidate_id);
CREATE INDEX IF NOT EXISTS idx_match_results_employer_id ON match_results(employer_id);
CREATE INDEX IF NOT EXISTS idx_match_results_pipeline_stage ON match_results(pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_match_results_overall_score ON match_results(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_match_results_created_at ON match_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_match_results_onboard_date ON match_results(onboard_date);

-- 复合索引优化常见查询
CREATE INDEX IF NOT EXISTS idx_match_results_job_stage ON match_results(job_id, pipeline_stage);
CREATE INDEX IF NOT EXISTS idx_match_results_candidate_stage ON match_results(candidate_id, pipeline_stage);

-- ---------------------------------------------------------------------------
-- 表 5: invoices (发票/账单表)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    -- 主键: UUID 类型
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 外键
    employer_id UUID NOT NULL REFERENCES employers(id) ON DELETE RESTRICT,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE RESTRICT,
    match_id UUID NOT NULL REFERENCES match_results(id) ON DELETE RESTRICT,

    -- 账单编号
    invoice_number VARCHAR(50) NOT NULL UNIQUE,

    -- 费用明细
    base_fee BIGINT NOT NULL DEFAULT 0,          -- 基础服务费 (分)
    screening_fee BIGINT NOT NULL DEFAULT 0,      -- 筛选费
    interview_fee BIGINT NOT NULL DEFAULT 0,     -- 面试安排费
    offer_fee BIGINT NOT NULL DEFAULT 0,         -- Offer 服务费
    guarantee_fee BIGINT NOT NULL DEFAULT 0,     -- 保障服务费
    urgent_premium BIGINT NOT NULL DEFAULT 0,    -- 急招溢价
    discount_amount BIGINT NOT NULL DEFAULT 0,    -- 折扣金额

    -- 计算字段
    subtotal BIGINT NOT NULL GENERATED ALWAYS AS (
        base_fee + screening_fee + interview_fee + offer_fee + guarantee_fee
    ) STORED,
    total_fee BIGINT NOT NULL GENERATED ALWAYS AS (
        base_fee + screening_fee + interview_fee + offer_fee + guarantee_fee + urgent_premium - discount_amount
    ) STORED,

    -- 佣金配置
    commission_rate FLOAT NOT NULL DEFAULT 0.10,
    commission_amount BIGINT GENERATED ALWAYS AS (
        CASE WHEN total_fee > 0
        THEN (total_fee * commission_rate)::BIGINT
        ELSE 0
        END
    ) STORED,

    -- 发票状态
    status invoice_status NOT NULL DEFAULT 'pending',

    -- 支付信息
    payment_method payment_method,
    payment_reference VARCHAR(100),
    payment_deadline TIMESTAMPTZ,

    -- 支付时间
    paid_at TIMESTAMPTZ,

    -- 发票抬头信息
    invoice_title VARCHAR(300),
    invoice_tax_number VARCHAR(50),
    invoice_content VARCHAR(100),

    -- 备注
    notes TEXT,

    -- 退款信息
    refund_amount BIGINT DEFAULT 0,
    refund_reason TEXT,
    refunded_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 约束
    CONSTRAINT invoices_fees_positive CHECK (
        base_fee >= 0 AND
        screening_fee >= 0 AND
        interview_fee >= 0 AND
        offer_fee >= 0 AND
        guarantee_fee >= 0 AND
        urgent_premium >= 0 AND
        discount_amount >= 0 AND
        refund_amount >= 0
    )
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_invoices_employer_id ON invoices(employer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_job_id ON invoices(job_id);
CREATE INDEX IF NOT EXISTS idx_invoices_match_id ON invoices(match_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_payment_deadline ON invoices(payment_deadline) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number);

-- ---------------------------------------------------------------------------
-- 表 6: guarantees (担保服务表)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guarantees (
    -- 主键: UUID 类型
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 外键
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
    match_id UUID NOT NULL REFERENCES match_results(id) ON DELETE RESTRICT,
    employer_id UUID NOT NULL REFERENCES employers(id) ON DELETE RESTRICT,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE RESTRICT,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE RESTRICT,

    -- 担保编号
    guarantee_number VARCHAR(50) NOT NULL UNIQUE,

    -- 担保期限
    start_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    guarantee_months INTEGER NOT NULL DEFAULT 3,  -- 担保月数

    -- 赔付配置
    compensation_amount BIGINT NOT NULL,  -- 赔付金额 (分)
    compensation_ratio FLOAT,              -- 赔付比例

    -- 担保状态
    status guarantee_status NOT NULL DEFAULT 'active',

    -- 赔付条款 (JSONB)
    terms JSONB NOT NULL DEFAULT '{}',
    /* terms 结构示例:
    {
        "conditions": [
            "候选人入职未满3个月离职",
            "非公司主动裁员",
            "候选人非因违法违纪被辞退"
        ],
        "exclusions": [
            "公司经营困难裁员",
            "候选人主动离职",
            "试用期考核不通过"
        ],
        "required_documents": [
            "解除劳动合同证明",
            "社保缴纳记录",
            "工资流水"
        ]
    }
    */

    -- 认领信息
    claim_submitted_at TIMESTAMPTZ,
    claim_reason TEXT,
    claim_status VARCHAR(50),  -- 'submitted', 'under_review', 'approved', 'rejected'
    claim_resolved_at TIMESTAMPTZ,
    claim_resolution_notes TEXT,

    -- 证据材料
    evidence_url TEXT,
    additional_evidence_urls TEXT[],

    -- 赔付处理
    approved_compensation BIGINT,  -- 批准赔付金额
    compensation_paid_at TIMESTAMPTZ,
    compensation_payment_reference VARCHAR(100),

    -- 备注
    internal_notes TEXT,

    -- 候选人确认
    candidate_confirmed BOOLEAN DEFAULT FALSE,
    candidate_confirmed_at TIMESTAMPTZ,
    employer_confirmed BOOLEAN DEFAULT FALSE,
    employer_confirmed_at TIMESTAMPTZ,

    -- 时间戳
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 约束
    CONSTRAINT guarantees_date_check CHECK (expiry_date > start_date),
    CONSTRAINT guarantees_compensation_positive CHECK (compensation_amount > 0)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_guarantees_invoice_id ON guarantees(invoice_id);
CREATE INDEX IF NOT EXISTS idx_guarantees_match_id ON guarantees(match_id);
CREATE INDEX IF NOT EXISTS idx_guarantees_employer_id ON guarantees(employer_id);
CREATE INDEX IF NOT EXISTS idx_guarantees_candidate_id ON guarantees(candidate_id);
CREATE INDEX IF NOT EXISTS idx_guarantees_status ON guarantees(status);
CREATE INDEX IF NOT EXISTS idx_guarantees_expiry_date ON guarantees(expiry_date) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_guarantees_created_at ON guarantees(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_guarantees_guarantee_number ON guarantees(guarantee_number);

-- ============================================================================
-- 第四部分: 辅助表
-- ============================================================================

-- 职位申请记录表
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id UUID NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    match_result_id UUID REFERENCES match_results(id) ON DELETE SET NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    cover_letter TEXT,
    source VARCHAR(50),  -- 'direct_apply', 'employer_invite', 'referral'

    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT applications_unique UNIQUE (job_id, candidate_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_candidate_id ON applications(candidate_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_applied_at ON applications(applied_at DESC);

-- 雇主操作日志表
CREATE TABLE IF NOT EXISTS employer_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employer_id UUID NOT NULL REFERENCES employers(id) ON DELETE CASCADE,

    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,

    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_employer_actions_employer ON employer_actions(employer_id);
CREATE INDEX IF NOT EXISTS idx_employer_actions_type ON employer_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_employer_actions_created ON employer_actions(created_at DESC);

-- ============================================================================
-- 第五部分: 触发器和函数
-- ============================================================================

-- 自动更新 updated_at 触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有表添加 updated_at 触发器
CREATE TRIGGER update_employers_updated_at
    BEFORE UPDATE ON employers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_match_results_updated_at
    BEFORE UPDATE ON match_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at
    BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_guarantees_updated_at
    BEFORE UPDATE ON guarantees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 生成账单编号的函数
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.invoice_number IS NULL THEN
        NEW.invoice_number := 'INV' || TO_CHAR(NOW(), 'YYYYMM') ||
                              LPAD(NEXTVAL('invoice_seq')::TEXT, 8, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE SEQUENCE IF NOT EXISTS invoice_seq START 1;

CREATE TRIGGER generate_invoice_number_trigger
    BEFORE INSERT ON invoices
    FOR EACH ROW EXECUTE FUNCTION generate_invoice_number();

-- 生成担保编号的函数
CREATE OR REPLACE FUNCTION generate_guarantee_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.guarantee_number IS NULL THEN
        NEW.guarantee_number := 'GRT' || TO_CHAR(NOW(), 'YYYYMM') ||
                                LPAD(NEXTVAL('guarantee_seq')::TEXT, 8, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE SEQUENCE IF NOT EXISTS guarantee_seq START 1;

CREATE TRIGGER generate_guarantee_number_trigger
    BEFORE INSERT ON guarantees
    FOR EACH ROW EXECUTE FUNCTION generate_guarantee_number();

-- 软删除触发器函数
CREATE OR REPLACE FUNCTION soft_delete_record()
RETURNS TRIGGER AS $$
BEGIN
    NEW.is_deleted = TRUE;
    NEW.deleted_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 自动更新 profile_completeness 的函数
CREATE OR REPLACE FUNCTION calculate_profile_completeness()
RETURNS TRIGGER AS $$
DECLARE
    completeness FLOAT := 0.0;
    profile_data JSONB;
BEGIN
    profile_data := NEW.profile;

    -- 计算各项完成度
    IF profile_data ? 'education' AND jsonb_array_length(profile_data->'education') > 0 THEN
        completeness := completeness + 0.15;
    END IF;

    IF profile_data ? 'work_experience' AND jsonb_array_length(profile_data->'work_experience') > 0 THEN
        completeness := completeness + 0.30;
    END IF;

    IF profile_data ? 'skills' AND jsonb_array_length(profile_data->'skills') > 0 THEN
        completeness := completeness + 0.20;
    END IF;

    IF NEW.expected_salary_min IS NOT NULL THEN
        completeness := completeness + 0.10;
    END IF;

    IF NEW.email IS NOT NULL AND NEW.email_verified THEN
        completeness := completeness + 0.10;
    END IF;

    IF NEW.resume_id IS NOT NULL THEN
        completeness := completeness + 0.15;
    END IF;

    NEW.profile_completeness := completeness;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_profile_completeness_trigger
    BEFORE INSERT OR UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION calculate_profile_completeness();

-- ============================================================================
-- 第六部分: 视图
-- ============================================================================

-- 活跃职位视图
CREATE OR REPLACE VIEW v_active_jobs AS
SELECT
    j.*,
    e.company_name,
    e.company_logo_url,
    e.is_verified AS employer_verified,
    COUNT(DISTINCT mr.id) AS total_matches,
    COUNT(DISTINCT CASE WHEN mr.pipeline_stage = 'onboarded' THEN mr.id END) AS total_hired
FROM jobs j
JOIN employers e ON j.employer_id = e.id
LEFT JOIN match_results mr ON j.id = mr.job_id
WHERE j.status = 'published' AND j.is_deleted = FALSE
GROUP BY j.id, e.company_name, e.company_logo_url, e.is_verified;

-- 匹配统计视图
CREATE OR REPLACE VIEW v_match_statistics AS
SELECT
    mr.employer_id,
    e.company_name,
    j.id AS job_id,
    j.job_title,
    COUNT(mr.id) AS total_matches,
    AVG(mr.overall_score) AS avg_match_score,
    COUNT(CASE WHEN mr.pipeline_stage = 'interview_scheduled' THEN 1 END) AS interview_count,
    COUNT(CASE WHEN mr.pipeline_stage = 'offer_sent' THEN 1 END) AS offer_count,
    COUNT(CASE WHEN mr.pipeline_stage = 'onboarded' THEN 1 END) AS hired_count,
    SUM(CASE WHEN mr.pipeline_stage = 'onboarded' THEN i.total_fee ELSE 0 END) AS total_revenue
FROM match_results mr
JOIN jobs j ON mr.job_id = j.id
JOIN employers e ON mr.employer_id = e.id
LEFT JOIN invoices i ON mr.id = i.match_id
GROUP BY mr.employer_id, e.company_name, j.id, j.job_title;

-- 候选人匹配视图
CREATE OR REPLACE VIEW v_candidate_matches AS
SELECT
    c.id AS candidate_id,
    c.name,
    c.job_search_status,
    c.profile_completeness,
    COUNT(DISTINCT mr.job_id) AS applied_jobs,
    COUNT(DISTINCT CASE WHEN mr.pipeline_stage = 'interview_scheduled' THEN mr.job_id END) AS interview_count,
    COUNT(DISTINCT CASE WHEN mr.pipeline_stage = 'offer_sent' THEN mr.job_id END) AS offer_count,
    MAX(mr.overall_score) AS best_match_score,
    AVG(mr.overall_score) AS avg_match_score
FROM candidates c
LEFT JOIN match_results mr ON c.id = mr.candidate_id
WHERE c.is_active = TRUE AND c.is_hidden = FALSE
GROUP BY c.id, c.name, c.job_search_status, c.profile_completeness;

-- 财务统计视图
CREATE OR REPLACE VIEW v_financial_summary AS
SELECT
    e.id AS employer_id,
    e.company_name,
    e.credit_balance,
    COUNT(DISTINCT i.id) AS total_invoices,
    SUM(i.total_fee) AS total_billed,
    SUM(CASE WHEN i.status = 'paid' THEN i.total_fee ELSE 0 END) AS total_paid,
    SUM(CASE WHEN i.status = 'pending' THEN i.total_fee ELSE 0 END) AS total_pending,
    SUM(i.commission_amount) AS total_commission
FROM employers e
LEFT JOIN invoices i ON e.id = i.employer_id
GROUP BY e.id, e.company_name, e.credit_balance;

-- 活跃担保视图
CREATE OR REPLACE VIEW v_active_guarantees AS
SELECT
    g.*,
    e.company_name,
    c.name AS candidate_name,
    j.job_title,
    i.total_fee AS invoice_amount,
    (g.expiry_date - CURRENT_DATE) AS days_remaining,
    (g.compensation_amount - COALESCE(g.approved_compensation, 0)) AS pending_compensation
FROM guarantees g
JOIN employers e ON g.employer_id = e.id
JOIN candidates c ON g.candidate_id = c.id
JOIN jobs j ON g.job_id = j.id
JOIN invoices i ON g.invoice_id = i.id
WHERE g.status IN ('active', 'claimed');

-- ============================================================================
-- 第七部分: 初始数据
-- ============================================================================

-- 插入测试雇主数据
INSERT INTO employers (
    company_name,
    industry,
    contact_name,
    contact_phone,
    kyc_status,
    is_verified,
    credit_balance
) VALUES
    ('HigherMatch Tech Inc.', 'Technology', 'Zhang Wei', '+86-138-0000-0001', 'approved', TRUE, 1000000),
    ('ByteDance China', 'Internet', 'Li Ming', '+86-139-0000-0002', 'approved', TRUE, 2000000),
    ('Alibaba Group', 'E-commerce', 'Wang Fang', '+86-137-0000-0003', 'approved', TRUE, 5000000)
ON CONFLICT DO NOTHING;

-- 插入测试候选人数据
INSERT INTO candidates (
    phone_hash,
    email,
    name,
    job_search_status,
    profile,
    verification_score,
    profile_completeness
) VALUES
    (
        encode(sha256('13800000001'::bytea), 'hex'),
        'candidate1@example.com',
        'Zhang San',
        'active',
        '{
            "education": [{"school": "Tsinghua University", "degree": "Master", "major": "Computer Science", "graduation_year": 2022}],
            "work_experience": [{"company": "Tencent", "title": "Software Engineer", "duration": "2022-Present"}],
            "skills": ["Python", "Go", "PostgreSQL", "Kubernetes"]
        }'::jsonb,
        0.85,
        0.75
    ),
    (
        encode(sha256('13800000002'::bytea), 'hex'),
        'candidate2@example.com',
        'Li Si',
        'passive',
        '{
            "education": [{"school": "Peking University", "degree": "Bachelor", "major": "Software Engineering", "graduation_year": 2021}],
            "work_experience": [{"company": "ByteDance", "title": "Backend Developer", "duration": "2021-Present"}],
            "skills": ["Java", "Spring Boot", "MySQL", "Redis"]
        }'::jsonb,
        0.90,
        0.80
    )
ON CONFLICT (phone_hash) DO NOTHING;

-- ============================================================================
-- 第八部分: 权限设置
-- ============================================================================

-- 创建应用用户 (可选)
-- CREATE USER highermatch_app WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE highermatch_dev TO highermatch_app;

-- 授予表权限
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO highermatch_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO highermatch_app;

-- ============================================================================
-- 完成
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'HigherMatch™ database schema created successfully!';
    RAISE NOTICE 'Tables created: employers, candidates, jobs, match_results, invoices, guarantees';
    RAISE NOTICE 'Views created: v_active_jobs, v_match_statistics, v_candidate_matches, v_financial_summary, v_active_guarantees';
    RAISE NOTICE 'Triggers and functions: update_updated_at_column, soft_delete, generate numbers';
END $$;
