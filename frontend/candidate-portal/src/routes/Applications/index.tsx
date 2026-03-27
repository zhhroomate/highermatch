/**
 * HigherMatch™ Candidate Portal - 申请追踪页面
 * ============================================
 * 展示投递岗位的流转状态
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  List,
  Tag,
  Skeleton,
  DotLoading,
  Empty,
  Badge,
} from 'antd-mobile';
import {
  CheckCircleFill,
  ClockCircleFill,
  VideoOutline,
  GiftOutline,
  UserAddOutline,
  StarOutline,
  CloseCircleFill,
} from 'antd-mobile-icons';
import './index.css';

// ==================== 类型定义 ====================

export type ApplicationStatus =
  | 'recommended'
  | 'invited'
  | 'interviewing'
  | 'offer'
  | 'hired'
  | 'rejected';

export interface Application {
  id: string;
  jobId: string;
  jobTitle: string;
  company: string;
  logo?: string;
  location: string;
  salary: string;
  status: ApplicationStatus;
  statusText: string;
  appliedAt: string;
  updateAt: string;
  timeline: TimelineEvent[];
}

export interface TimelineEvent {
  id: string;
  status: ApplicationStatus;
  title: string;
  description?: string;
  time: string;
}

// ==================== 配置 ====================

const STATUS_CONFIG: Record<
  ApplicationStatus,
  { color: string; bgColor: string; icon: React.ReactNode; label: string }
> = {
  recommended: {
    color: '#1890ff',
    bgColor: '#e6f7ff',
    icon: <StarOutline />,
    label: 'AI推荐',
  },
  invited: {
    color: '#722ed1',
    bgColor: '#f9f0ff',
    icon: <CheckCircleFill />,
    label: '已邀约',
  },
  interviewing: {
    color: '#fa8c16',
    bgColor: '#fff7e6',
    icon: <VideoOutline />,
    label: '面试中',
  },
  offer: {
    color: '#52c41a',
    bgColor: '#f6ffed',
    icon: <GiftOutline />,
    label: '待入职',
  },
  hired: {
    color: '#13c2c2',
    bgColor: '#e6fffb',
    icon: <UserAddOutline />,
    label: '已入职',
  },
  rejected: {
    color: '#ff4d4f',
    bgColor: '#fff1f0',
    icon: <CloseCircleFill />,
    label: '已拒绝',
  },
};

// ==================== 组件 ====================

/**
 * 状态标签
 */
const StatusTag: React.FC<{ status: ApplicationStatus }> = ({ status }) => {
  const config = STATUS_CONFIG[status];
  return (
    <Tag color={config.color} fill="solid" className="status-tag">
      {config.icon}
      <span>{config.label}</span>
    </Tag>
  );
};

/**
 * 时间线节点
 */
const TimelineNode: React.FC<{
  event: TimelineEvent;
  isFirst: boolean;
  isLast: boolean;
  isActive: boolean;
}> = ({ event, isFirst, isLast, isActive }) => {
  const config = STATUS_CONFIG[event.status];
  const isCompleted = ['hired', 'rejected'].includes(event.status);

  return (
    <div
      className={`timeline-node ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
    >
      <div className="node-line top-line">
        {!isFirst && <div className="line-fill" style={{ background: isActive || isCompleted ? config.color : '#ddd' }} />}
      </div>

      <div className="node-dot" style={{ background: config.bgColor, borderColor: config.color }}>
        <span style={{ color: config.color }}>{config.icon}</span>
      </div>

      <div className="node-line bottom-line">
        {!isLast && <div className="line-fill pending" />}
      </div>

      <div className="node-content">
        <div className="node-header">
          <span className="node-title">{event.title}</span>
          <span className="node-time">{event.time}</span>
        </div>
        {event.description && (
          <p className="node-desc">{event.description}</p>
        )}
      </div>
    </div>
  );
};

/**
 * 申请卡片
 */
const ApplicationCard: React.FC<{
  application: Application;
}> = ({ application }) => {
  const [expanded, setExpanded] = useState(false);
  const currentStatusIndex = ['recommended', 'invited', 'interviewing', 'offer', 'hired'].indexOf(application.status);

  return (
    <div className="application-card">
      <div
        className="card-header"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="card-info">
          <div className="card-title-row">
            <h3 className="job-title">{application.jobTitle}</h3>
            <StatusTag status={application.status} />
          </div>
          <p className="company-info">
            {application.company} · {application.location}
          </p>
          <div className="salary-row">
            <span className="salary">{application.salary}</span>
            <span className="applied-time">投递于 {application.appliedAt}</span>
          </div>
        </div>

        <div className={`expand-icon ${expanded ? 'expanded' : ''}`}>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
            <path d="M2 4L6 8L10 4" stroke="currentColor" strokeWidth="2" fill="none" />
          </svg>
        </div>
      </div>

      {/* 进度指示器 */}
      <div className="progress-indicator">
        {Object.entries(STATUS_CONFIG)
          .filter(([key]) => !['rejected'].includes(key))
          .map(([key, config], index) => (
            <div
              key={key}
              className={`progress-step ${index <= currentStatusIndex ? 'active' : ''} ${index === currentStatusIndex ? 'current' : ''}`}
              style={{ '--step-color': config.color } as React.CSSProperties}
            >
              <div className="step-dot">
                {index < currentStatusIndex && <CheckCircleFill />}
                {index === currentStatusIndex && config.icon}
                {index > currentStatusIndex && <ClockCircleFill />}
              </div>
              <span className="step-label">{config.label}</span>
            </div>
          ))}
      </div>

      {/* 时间线详情 */}
      {expanded && (
        <div className="timeline-section">
          <div className="timeline-title">申请进度</div>
          <div className="timeline">
            {application.timeline.map((event, index) => (
              <TimelineNode
                key={event.id}
                event={event}
                isFirst={index === 0}
                isLast={index === application.timeline.length - 1}
                isActive={index === application.timeline.length - 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * 申请追踪页面
 */
const Applications: React.FC = () => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'completed'>('all');

  // 模拟加载申请数据
  useEffect(() => {
    const fetchApplications = async () => {
      setLoading(true);
      try {
        await new Promise((resolve) => setTimeout(resolve, 800));

        const mockData: Application[] = [
          {
            id: '1',
            jobId: 'job-1',
            jobTitle: '高级前端工程师',
            company: '字节跳动',
            location: '北京',
            salary: '35K-55K',
            status: 'interviewing',
            statusText: '面试中',
            appliedAt: '2024-03-15',
            updateAt: '2024-03-18',
            timeline: [
              {
                id: 't1',
                status: 'recommended',
                title: 'AI智能推荐',
                description: '系统根据您的简历自动推荐该职位',
                time: '2024-03-14',
              },
              {
                id: 't2',
                status: 'invited',
                title: '收到面试邀请',
                description: 'HR 认为您非常适合该岗位',
                time: '2024-03-15',
              },
              {
                id: 't3',
                status: 'interviewing',
                title: '一面完成',
                description: '技术面试通过，等待二面通知',
                time: '2024-03-18',
              },
            ],
          },
          {
            id: '2',
            jobId: 'job-2',
            jobTitle: '资深算法工程师',
            company: '阿里巴巴',
            location: '杭州',
            salary: '40K-70K',
            status: 'offer',
            statusText: '待入职',
            appliedAt: '2024-03-10',
            updateAt: '2024-03-19',
            timeline: [
              {
                id: 't1',
                status: 'recommended',
                title: 'AI智能推荐',
                time: '2024-03-09',
              },
              {
                id: 't2',
                status: 'invited',
                title: '收到面试邀请',
                time: '2024-03-10',
              },
              {
                id: 't3',
                status: 'interviewing',
                title: '三面全部通过',
                time: '2024-03-16',
              },
              {
                id: 't4',
                status: 'offer',
                title: '收到 Offer',
                description: '薪资待遇满意，等待入职确认',
                time: '2024-03-19',
              },
            ],
          },
          {
            id: '3',
            jobId: 'job-3',
            jobTitle: '产品经理',
            company: '腾讯',
            location: '深圳',
            salary: '30K-45K',
            status: 'invited',
            statusText: '已邀约',
            appliedAt: '2024-03-17',
            updateAt: '2024-03-19',
            timeline: [
              {
                id: 't1',
                status: 'recommended',
                title: 'AI智能推荐',
                time: '2024-03-16',
              },
              {
                id: 't2',
                status: 'invited',
                title: '收到面试邀请',
                description: '简历通过筛选，等待面试安排',
                time: '2024-03-19',
              },
            ],
          },
          {
            id: '4',
            jobId: 'job-4',
            jobTitle: 'Java 高级开发',
            company: '华为',
            location: '深圳',
            salary: '28K-45K',
            status: 'rejected',
            statusText: '已拒绝',
            appliedAt: '2024-03-08',
            updateAt: '2024-03-15',
            timeline: [
              {
                id: 't1',
                status: 'recommended',
                title: 'AI智能推荐',
                time: '2024-03-07',
              },
              {
                id: 't2',
                status: 'rejected',
                title: '面试未通过',
                description: '技术面试未达到岗位要求',
                time: '2024-03-15',
              },
            ],
          },
        ];

        setApplications(mockData);
      } catch (error) {
        console.error('Failed to fetch applications:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchApplications();
  }, []);

  // 过滤申请
  const filteredApplications = applications.filter((app) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'active') return !['hired', 'rejected'].includes(app.status);
    if (activeTab === 'completed') return ['hired', 'rejected'].includes(app.status);
    return true;
  });

  // 统计
  const stats = {
    total: applications.length,
    active: applications.filter((a) => !['hired', 'rejected'].includes(a.status)).length,
    offer: applications.filter((a) => a.status === 'offer').length,
    hired: applications.filter((a) => a.status === 'hired').length,
  };

  return (
    <div className="applications-page">
      <div className="page-header">
        <h1>我的申请</h1>
        <p className="header-tip">追踪您的求职进度</p>
      </div>

      {/* 统计卡片 */}
      <div className="stats-section">
        <div className="stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">全部申请</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.active}</div>
          <div className="stat-label">进行中</div>
        </div>
        <div className="stat-card highlight">
          <div className="stat-value">{stats.offer}</div>
          <div className="stat-label">Offer</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.hired}</div>
          <div className="stat-label">已入职</div>
        </div>
      </div>

      {/* 筛选标签 */}
      <div className="filter-tabs">
        <Badge content={stats.total}>
          <div
            className={`tab-item ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            全部
          </div>
        </Badge>
        <Badge content={stats.active}>
          <div
            className={`tab-item ${activeTab === 'active' ? 'active' : ''}`}
            onClick={() => setActiveTab('active')}
          >
            进行中
          </div>
        </Badge>
        <div
          className={`tab-item ${activeTab === 'completed' ? 'active' : ''}`}
          onClick={() => setActiveTab('completed')}
        >
          已结束
        </div>
      </div>

      {/* 申请列表 */}
      <div className="applications-list">
        {loading ? (
          <div className="loading-state">
            <DotLoading />
            <span>加载中...</span>
          </div>
        ) : filteredApplications.length === 0 ? (
          <Empty description="暂无申请记录" />
        ) : (
          filteredApplications.map((app) => (
            <ApplicationCard key={app.id} application={app} />
          ))
        )}
      </div>
    </div>
  );
};

export default Applications;
