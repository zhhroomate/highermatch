/**
 * HigherMatch™ Candidate Portal - 职位推荐页面
 * ============================================
 * 基于 AI 匹配的职位推荐列表
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Swiper,
  Card,
  Tag,
  Button,
  Skeleton,
  Toast,
  DotLoading,
  Card as MobileCard,
} from 'antd-mobile';
import {
  FireFill,
  CheckCircleFill,
  EnvironmentOutline,
  BillOutline,
  ClockCircleOutline,
} from 'antd-mobile-icons';
import { apiClient } from '../../api/client';
import './index.css';

// ==================== 类型定义 ====================

export interface JobRecommendation {
  id: string;
  title: string;
  company: string;
  companyLogo?: string;
  location: string;
  salary: string;
  matchScore: number;
  matchReason: string;
  tags: string[];
  postedAt: string;
  isTop: boolean;
}

// ==================== 组件 ====================

/**
 * 职位推荐卡片
 */
const JobCard: React.FC<{
  job: JobRecommendation;
  onApply: (jobId: string) => void;
  isApplying: boolean;
}> = ({ job, onApply, isApplying }) => {
  const getMatchColor = (score: number) => {
    if (score >= 90) return '#52c41a';
    if (score >= 80) return '#1890ff';
    if (score >= 70) return '#faad14';
    return '#999';
  };

  return (
    <div className="job-card">
      {job.isTop && (
        <div className="top-badge">
          <FireFill /> 置顶推荐
        </div>
      )}

      <div className="job-header">
        <div className="job-info">
          <h3 className="job-title">{job.title}</h3>
          <p className="company-name">{job.company}</p>
        </div>
        <div
          className="match-score"
          style={{ background: getMatchColor(job.matchScore) }}
        >
          <span className="score-value">{job.matchScore}</span>
          <span className="score-label">匹配</span>
        </div>
      </div>

      <div className="job-meta">
        <span className="meta-item">
          <EnvironmentOutline /> {job.location}
        </span>
        <span className="meta-item">
          <BillOutline /> {job.salary}
        </span>
        <span className="meta-item">
          <ClockCircleOutline /> {job.postedAt}
        </span>
      </div>

      <div className="match-reason">
        <span className="reason-label">推荐理由：</span>
        {job.matchReason}
      </div>

      <div className="job-tags">
        {job.tags.map((tag) => (
          <Tag key={tag} color="primary" fill="outline">
            {tag}
          </Tag>
        ))}
      </div>

      <Button
        block
        color="primary"
        size="small"
        loading={isApplying}
        onClick={() => onApply(job.id)}
        className="apply-btn"
      >
        一键申请
      </Button>
    </div>
  );
};

/**
 * 推荐职位轮播卡片
 */
const FeaturedJobCard: React.FC<{
  job: JobRecommendation;
  onApply: (jobId: string) => void;
  isApplying: boolean;
}> = ({ job, onApply, isApplying }) => {
  return (
    <div className="featured-job-card">
      <div className="featured-header">
        <div className="featured-badge">
          <FireFill /> 为你精选
        </div>
        <div className="featured-match" style={{ color: '#ff6b00' }}>
          {job.matchScore}% AI 匹配
        </div>
      </div>

      <h3 className="featured-title">{job.title}</h3>
      <p className="featured-company">{job.company}</p>

      <div className="featured-reason">
        <CheckCircleFill style={{ color: '#52c41a' }} />
        <span>{job.matchReason}</span>
      </div>

      <div className="featured-footer">
        <span className="featured-salary">{job.salary}</span>
        <Button
          size="small"
          color="primary"
          loading={isApplying}
          onClick={() => onApply(job.id)}
        >
          立即申请
        </Button>
      </div>
    </div>
  );
};

/**
 * 职位推荐页面
 */
const Recommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<JobRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [applyingId, setApplyingId] = useState<string | null>(null);

  // 模拟加载推荐数据
  useEffect(() => {
    const fetchRecommendations = async () => {
      setLoading(true);
      try {
        // 模拟 API 调用
        await new Promise((resolve) => setTimeout(resolve, 800));

        // 模拟数据
        const mockData: JobRecommendation[] = [
          {
            id: '1',
            title: '高级前端工程师',
            company: '字节跳动',
            location: '北京·海淀区',
            salary: '35K-55K',
            matchScore: 95,
            matchReason: '您的 React 经验与岗位需求高度匹配',
            tags: ['React', 'TypeScript', '前端'],
            postedAt: '3天前发布',
            isTop: true,
          },
          {
            id: '2',
            title: '资深算法工程师',
            company: '阿里巴巴',
            location: '杭州·西湖区',
            salary: '40K-70K',
            matchScore: 88,
            matchReason: 'AI/ML 背景与推荐算法岗位完美契合',
            tags: ['Python', 'TensorFlow', '算法'],
            postedAt: '1周前发布',
            isTop: true,
          },
          {
            id: '3',
            title: '产品经理',
            company: '腾讯',
            location: '深圳·南山区',
            salary: '30K-45K',
            matchScore: 82,
            matchReason: '您的 B 端产品经验与岗位匹配',
            tags: ['B端', 'SaaS', '产品设计'],
            postedAt: '2天前发布',
            isTop: false,
          },
          {
            id: '4',
            title: 'Java 高级开发',
            company: '华为',
            location: '深圳·龙岗区',
            salary: '28K-45K',
            matchScore: 76,
            matchReason: '分布式系统经验符合岗位要求',
            tags: ['Java', 'Spring', '微服务'],
            postedAt: '5天前发布',
            isTop: false,
          },
        ];

        setRecommendations(mockData);
      } catch (error) {
        Toast.show('加载失败，请重试');
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  // 申请职位
  const handleApply = async (jobId: string) => {
    setApplyingId(jobId);
    try {
      // 模拟 API 调用
      await new Promise((resolve) => setTimeout(resolve, 1500));

      Toast.show({
        content: '申请成功！HR 将尽快处理您的简历',
        icon: 'success',
        position: 'top',
      });
    } catch (error) {
      Toast.show({
        content: '申请失败，请重试',
        icon: 'fail',
      });
    } finally {
      setApplyingId(null);
    }
  };

  const topJobs = recommendations.filter((j) => j.isTop).slice(0, 3);
  const allJobs = recommendations;

  return (
    <div className="recommendations-page">
      <div className="page-header">
        <h1>为你推荐</h1>
        <p className="header-tip">基于您的技能和求职偏好精挑细选</p>
      </div>

      {/* 顶部轮播 - Top 3 推荐 */}
      {loading ? (
        <div className="featured-skeleton">
          <Skeleton animated style={{ height: '180px', borderRadius: '12px' }} />
        </div>
      ) : (
        <div className="featured-section">
          <Swiper
            loop
            autoplay
            autoplayInterval={4000}
            indicator={() => null}
          >
            {topJobs.map((job) => (
              <Swiper.Item key={job.id}>
                <FeaturedJobCard
                  job={job}
                  onApply={handleApply}
                  isApplying={applyingId === job.id}
                />
              </Swiper.Item>
            ))}
          </Swiper>

          {/* 自定义指示器 */}
          <div className="custom-indicator">
            {topJobs.map((_, index) => (
              <span key={index} className="dot" />
            ))}
          </div>
        </div>
      )}

      {/* 全部推荐列表 */}
      <div className="recommendations-list">
        <h2 className="section-title">
          <span className="title-text">更多推荐</span>
          <span className="title-count">{allJobs.length} 个职位</span>
        </h2>

        {loading ? (
          <div className="loading-state">
            <DotLoading />
            <span>正在加载推荐...</span>
          </div>
        ) : (
          <div className="job-list">
            {allJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onApply={handleApply}
                isApplying={applyingId === job.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Recommendations;
