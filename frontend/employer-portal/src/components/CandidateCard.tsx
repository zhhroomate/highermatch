/**
 * HigherMatch™ Employer Portal - 候选人卡片组件
 * ============================================
 * 管道看板中的候选人卡片
 * 支持模糊头像、姓名脱敏、环形匹配分
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect, memo } from 'react';
import { Tag, Typography, Space, Avatar, Tooltip, Badge } from 'antd';
import {
  EnvironmentOutlined,
  ClockCircleOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { apiClient } from '../api/client';

const { Text } = Typography;

/**
 * 候选人数据类型
 */
export interface Candidate {
  id: string;
  name: string;
  avatar?: string;
  city: string;
  experienceYears: number;
  matchScore: number; // 0-100
  stage: string;
  skills: string[];
  lastUpdated?: string;
  source?: string;
}

interface CandidateCardProps {
  candidate: Candidate;
  isDragging?: boolean;
  isFlashing?: boolean;
  onClick?: (candidate: Candidate) => void;
}

/**
 * 环形进度条组件
 */
const ScoreRing: React.FC<{ score: number; size?: number }> = ({ score, size = 48 }) => {
  const radius = (size - 6) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // 根据分数确定颜色
  const getColor = () => {
    if (score >= 80) return '#52c41a';
    if (score >= 60) return '#faad14';
    return '#ff4d4f';
  };

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
      }}
    >
      <svg
        width={size}
        height={size}
        style={{ transform: 'rotate(-90deg)' }}
      >
        {/* 背景圆环 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#f0f0f0"
          strokeWidth={4}
        />
        {/* 进度圆环 */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={getColor()}
          strokeWidth={4}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 0.5s ease',
          }}
        />
      </svg>
      {/* 中心分数 */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          fontSize: size < 50 ? 10 : 12,
          fontWeight: 'bold',
          color: getColor(),
        }}
      >
        {score}
      </div>
    </div>
  );
};

/**
 * 模糊头像组件
 */
const BlurAvatar: React.FC<{ src?: string; name: string; size?: number }> = ({
  src,
  name,
  size = 48,
}) => {
  const [imageError, setImageError] = useState(false);

  // 获取名字首字母
  const getInitials = (name: string) => {
    return name.charAt(0).toUpperCase();
  };

  // 生成背景颜色
  const getBackgroundColor = (name: string) => {
    const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];
    const index = name.charCodeAt(0) % colors.length;
    return colors[index];
  };

  if (!src || imageError) {
    return (
      <div
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          backgroundColor: getBackgroundColor(name),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: size / 2.5,
          fontWeight: 'bold',
        }}
      >
        {getInitials(name)}
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        borderRadius: '50%',
        overflow: 'hidden',
      }}
    >
      <img
        src={src}
        alt={name}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          filter: 'blur(8px)',
        }}
        onError={() => setImageError(true)}
      />
      {/* 覆盖层 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
          color: '#fff',
          fontSize: size / 2.5,
          fontWeight: 'bold',
        }}
      >
        {getInitials(name)}
      </div>
    </div>
  );
};

/**
 * 候选人卡片组件
 */
const CandidateCard: React.FC<CandidateCardProps> = memo(({
  candidate,
  isDragging = false,
  isFlashing = false,
  onClick,
}) => {
  // 姓名脱敏：名用 * 代替
  const maskName = (name: string) => {
    if (name.length <= 1) return '*';
    return name.charAt(0) + '*'.repeat(name.length - 1);
  };

  // 获取匹配分颜色
  const getScoreColor = () => {
    if (candidate.matchScore >= 80) return '#52c41a';
    if (candidate.matchScore >= 60) return '#faad14';
    return '#ff4d4f';
  };

  // 获取匹配分标签
  const getScoreTag = () => {
    if (candidate.matchScore >= 80) {
      return <Tag color="success" style={{ marginRight: 0 }}>优秀</Tag>;
    }
    if (candidate.matchScore >= 60) {
      return <Tag color="warning" style={{ marginRight: 0 }}>良好</Tag>;
    }
    return <Tag color="error" style={{ marginRight: 0 }}>一般</Tag>;
  };

  return (
    <div
      onClick={() => onClick?.(candidate)}
      style={{
        padding: 12,
        marginBottom: 8,
        background: '#fff',
        borderRadius: 8,
        border: '1px solid #f0f0f0',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        opacity: isDragging ? 0.8 : 1,
        boxShadow: isDragging ? '0 4px 12px rgba(0, 0, 0, 0.15)' : 'none',
        transform: isDragging ? 'scale(1.02)' : 'scale(1)',
        animation: isFlashing ? 'flash 1s ease-in-out 3' : 'none',
        position: 'relative',
      }}
      onMouseEnter={(e) => {
        if (!isDragging) {
          e.currentTarget.style.borderColor = '#1890ff';
          e.currentTarget.style.boxShadow = '0 2px 8px rgba(24, 144, 255, 0.2)';
        }
      }}
      onMouseLeave={(e) => {
        if (!isDragging) {
          e.currentTarget.style.borderColor = '#f0f0f0';
          e.currentTarget.style.boxShadow = 'none';
        }
      }}
    >
      {/* 闪烁动画指示器 */}
      {isFlashing && (
        <div
          style={{
            position: 'absolute',
            top: 4,
            right: 4,
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: '#1890ff',
            animation: 'pulse 1s infinite',
          }}
        />
      )}

      <div style={{ display: 'flex', gap: 12 }}>
        {/* 左侧：模糊头像 */}
        <BlurAvatar
          src={candidate.avatar}
          name={candidate.name}
          size={48}
        />

        {/* 中间：信息 */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* 姓名脱敏 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <Text strong style={{ fontSize: 14 }}>{maskName(candidate.name)}</Text>
            {getScoreTag()}
          </div>

          {/* 城市和年限 */}
          <Space size={12} style={{ marginBottom: 6 }}>
            <Tooltip title="所在城市">
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <EnvironmentOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>{candidate.city}</Text>
              </span>
            </Tooltip>
            <Tooltip title="工作年限">
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <ClockCircleOutlined style={{ color: '#8c8c8c', fontSize: 12 }} />
                <Text type="secondary" style={{ fontSize: 12 }}>{candidate.experienceYears}年</Text>
              </span>
            </Tooltip>
          </Space>

          {/* 技能标签 */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {candidate.skills.slice(0, 3).map((skill, index) => (
              <Tag
                key={index}
                style={{
                  fontSize: 10,
                  padding: '0 4px',
                  margin: 0,
                  lineHeight: '18px',
                }}
              >
                {skill}
              </Tag>
            ))}
            {candidate.skills.length > 3 && (
              <Tag
                style={{
                  fontSize: 10,
                  padding: '0 4px',
                  margin: 0,
                  lineHeight: '18px',
                  background: '#f0f0f0',
                  border: 'none',
                }}
              >
                +{candidate.skills.length - 3}
              </Tag>
            )}
          </div>
        </div>

        {/* 右侧：环形匹配分 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <ScoreRing score={candidate.matchScore} size={48} />
          <div style={{ marginTop: 4 }}>
            <Tooltip title={`匹配度 ${candidate.matchScore}%`}>
              <span
                style={{
                  fontSize: 10,
                  color: getScoreColor(),
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                }}
              >
                <StarOutlined />
              </span>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* 最后更新时间 */}
      {candidate.lastUpdated && (
        <div
          style={{
            marginTop: 8,
            paddingTop: 8,
            borderTop: '1px solid #f0f0f0',
          }}
        >
          <Text type="secondary" style={{ fontSize: 10 }}>
            更新于 {candidate.lastUpdated}
          </Text>
        </div>
      )}

      <style>{`
        @keyframes flash {
          0%, 100% {
            background-color: #fff;
          }
          50% {
            background-color: #e6f7ff;
          }
        }
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(1.2);
          }
        }
      `}</style>
    </div>
  );
});

CandidateCard.displayName = 'CandidateCard';

export default CandidateCard;
export { ScoreRing, BlurAvatar };
