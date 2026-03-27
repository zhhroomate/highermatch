/**
 * HigherMatch™ Employer Portal - Dashboard 页面
 * ============================================
 *
 * 雇主端工作台主页面
 *
 * 功能：
 * 1. 顶部 4 个统计卡片
 * 2. 中间 Recharts LineChart 趋势图
 * 3. 底部待办事项列表
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect } from 'react';
import { Row, Col, Statistic, List, Tag, Button, Typography, Space, Empty, Card } from 'antd';
import {
  FundProjectionScreenOutlined,
  TeamOutlined,
  UserAddOutlined,
  ClockCircleOutlined,
  RightOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';

// ==================== 类型定义 ====================

interface StatCard {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  suffix?: string;
  trend?: number;
}

interface TrendData {
  date: string;
  candidates: number;
  applications: number;
  hires: number;
}

interface TodoItem {
  id: string;
  title: string;
  description: string;
  type: 'interview' | 'feedback' | 'approval' | 'reminder';
  priority: 'high' | 'medium' | 'low';
  dueDate: string;
  candidateName?: string;
  jobTitle?: string;
}

// ==================== Mock 数据 ====================

const mockTrendData: TrendData[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date();
  date.setDate(date.getDate() - (29 - i));
  return {
    date: `${date.getMonth() + 1}/${date.getDate()}`,
    candidates: Math.floor(Math.random() * 50) + 20 + i * 2,
    applications: Math.floor(Math.random() * 80) + 30 + i * 3,
    hires: Math.floor(Math.random() * 5) + 1,
  };
});

const mockTodoItems: TodoItem[] = [
  {
    id: '1',
    title: '张三的面试反馈待提交',
    description: 'Python 后端工程师岗位面试已结束，请尽快提交面试反馈',
    type: 'feedback',
    priority: 'high',
    dueDate: '今天',
    candidateName: '张三',
    jobTitle: 'Python 后端工程师',
  },
  {
    id: '2',
    title: '李四的 offer 待审批',
    description: '高级 Java 工程师 offer 金额 ¥35,000/月，需主管审批',
    type: 'approval',
    priority: 'high',
    dueDate: '明天',
    candidateName: '李四',
    jobTitle: '高级 Java 工程师',
  },
  {
    id: '3',
    title: '王五面试提醒',
    description: '产品经理岗位面试将于明天下午 2:00 进行',
    type: 'interview',
    priority: 'medium',
    dueDate: '明天',
    candidateName: '王五',
    jobTitle: '产品经理',
  },
  {
    id: '4',
    title: '新人入职跟进',
    description: '赵六将于下周一入职，请准备入职相关事宜',
    type: 'reminder',
    priority: 'medium',
    dueDate: '3天后',
  },
  {
    id: '5',
    title: '面试反馈待提交',
    description: '前端工程师岗位面试已结束 3 天，请尽快提交反馈',
    type: 'feedback',
    priority: 'low',
    dueDate: '本周内',
    candidateName: '钱七',
    jobTitle: '前端工程师',
  },
];

// ==================== 统计卡片组件 ====================

interface StatCardProps {
  stat: StatCard;
}

const StatCardComponent: React.FC<StatCardProps> = ({ stat }) => {
  return (
    <Card
      bordered={false}
      style={{
        borderRadius: 12,
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        height: 140,
      }}
      styles={{ body: { padding: 24, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ color: '#8c8c8c', fontSize: 14, marginBottom: 8 }}>{stat.title}</div>
          <div style={{ fontSize: 32, fontWeight: 600, color: '#262626' }}>
            {stat.value.toLocaleString()}
            {stat.suffix && <span style={{ fontSize: 16, color: '#8c8c8c', marginLeft: 4 }}>{stat.suffix}</span>}
          </div>
        </div>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            background: `${stat.color}15`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 24,
          }}
        >
          {stat.icon}
        </div>
      </div>
      {stat.trend !== undefined && (
        <div style={{ fontSize: 12, color: stat.trend >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {stat.trend >= 0 ? '↑' : '↓'} {Math.abs(stat.trend)}% 较上周
        </div>
      )}
    </Card>
  );
};

// ==================== 趋势图组件 ====================

interface TrendChartProps {
  data: TrendData[];
}

const TrendChart: React.FC<TrendChartProps> = ({ data }) => {
  return (
    <Card
      title={
        <span style={{ fontSize: 16, fontWeight: 600 }}>
          📈 最近30天候选人流入趋势
        </span>
      }
      extra={
        <Space size={16}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#1890ff' }} />
            <span style={{ fontSize: 12, color: '#666' }}>候选人</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#722ed1' }} />
            <span style={{ fontSize: 12, color: '#666' }}>投递</span>
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#52c41a' }} />
            <span style={{ fontSize: 12, color: '#666' }}>入职</span>
          </span>
        </Space>
      }
      bordered={false}
      style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
      styles={{ body: { padding: '16px 24px 24px' } }}
    >
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorCandidates" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1890ff" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#1890ff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorApplications" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#722ed1" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#722ed1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#8c8c8c' }}
            tickLine={false}
            axisLine={{ stroke: '#f0f0f0' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#8c8c8c' }}
            tickLine={false}
            axisLine={{ stroke: '#f0f0f0' }}
          />
          <Tooltip
            contentStyle={{
              background: '#fff',
              border: '1px solid #f0f0f0',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          />
          <Area
            type="monotone"
            dataKey="candidates"
            stroke="#1890ff"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorCandidates)"
            name="候选人"
          />
          <Area
            type="monotone"
            dataKey="applications"
            stroke="#722ed1"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorApplications)"
            name="投递"
          />
          <Line
            type="monotone"
            dataKey="hires"
            stroke="#52c41a"
            strokeWidth={2}
            dot={{ fill: '#52c41a', strokeWidth: 0, r: 3 }}
            activeDot={{ r: 5, strokeWidth: 0 }}
            name="入职"
          />
        </AreaChart>
      </ResponsiveContainer>
    </Card>
  );
};

// ==================== 待办事项组件 ====================

interface TodoListProps {
  items: TodoItem[];
  onItemClick?: (item: TodoItem) => void;
  onComplete?: (itemId: string) => void;
}

const TodoList: React.FC<TodoListProps> = ({ items, onItemClick, onComplete }) => {
  const getTypeIcon = (type: TodoItem['type']) => {
    switch (type) {
      case 'interview':
        return '📅';
      case 'feedback':
        return '📝';
      case 'approval':
        return '✅';
      case 'reminder':
        return '⏰';
      default:
        return '📋';
    }
  };

  const getPriorityColor = (priority: TodoItem['priority']) => {
    switch (priority) {
      case 'high':
        return '#ff4d4f';
      case 'medium':
        return '#faad14';
      case 'low':
        return '#52c41a';
      default:
        return '#d9d9d9';
    }
  };

  const getPriorityTag = (priority: TodoItem['priority']) => {
    const colors: Record<string, string> = {
      high: 'red',
      medium: 'orange',
      low: 'green',
    };
    const labels: Record<string, string> = {
      high: '紧急',
      medium: '一般',
      low: '低',
    };
    return <Tag color={colors[priority]}>{labels[priority]}</Tag>;
  };

  if (items.length === 0) {
    return (
      <Card
        title={
          <span style={{ fontSize: 16, fontWeight: 600 }}>
            📋 待办事项
          </span>
        }
        bordered={false}
        style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
      >
        <Empty description="暂无待办事项" />
      </Card>
    );
  }

  return (
    <Card
      title={
        <span style={{ fontSize: 16, fontWeight: 600 }}>
          📋 待办事项
          <Tag color="blue" style={{ marginLeft: 8 }}>
            {items.length} 项
          </Tag>
        </span>
      }
      extra={
        <Button type="link" size="small" style={{ color: '#1890ff' }}>
          查看全部 <RightOutlined />
        </Button>
      }
      bordered={false}
      style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
      styles={{ body: { padding: 0 } }}
    >
      <List
        dataSource={items}
        renderItem={(item) => (
          <List.Item
            style={{ padding: '16px 24px', cursor: 'pointer' }}
            onClick={() => onItemClick?.(item)}
            actions={[
              <Button
                key="complete"
                type="text"
                icon={<CheckCircleOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  onComplete?.(item.id);
                }}
                style={{ color: '#52c41a' }}
              >
                完成
              </Button>,
            ]}
          >
            <List.Item.Meta
              avatar={
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    background: `${getPriorityColor(item.priority)}15`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 18,
                  }}
                >
                  {getTypeIcon(item.type)}
                </div>
              }
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 14 }}>{item.title}</span>
                  {getPriorityTag(item.priority)}
                </div>
              }
              description={
                <div>
                  <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                    {item.description}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                    {item.candidateName && (
                      <span style={{ fontSize: 12, color: '#1890ff' }}>
                        👤 {item.candidateName}
                      </span>
                    )}
                    {item.jobTitle && (
                      <span style={{ fontSize: 12, color: '#722ed1' }}>
                        💼 {item.jobTitle}
                      </span>
                    )}
                    <span
                      style={{
                        fontSize: 12,
                        color: item.priority === 'high' ? '#ff4d4f' : '#8c8c8c',
                      }}
                    >
                      ⏰ {item.dueDate}
                    </span>
                  </div>
                </div>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
};

// ==================== 主 Dashboard 组件 ====================

/**
 * Dashboard 主页面
 */
const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [statCards, setStatCards] = useState<StatCard[]>([]);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [todoItems, setTodoItems] = useState<TodoItem[]>([]);

  // 模拟加载数据
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);

      // 模拟 API 延迟
      await new Promise((resolve) => setTimeout(resolve, 800));

      // 设置统计数据
      setStatCards([
        {
          title: '活跃岗位数',
          value: 12,
          icon: <FundProjectionScreenOutlined style={{ color: '#1890ff' }} />,
          color: '#1890ff',
          trend: 8.5,
        },
        {
          title: '候选人总数',
          value: 2456,
          icon: <TeamOutlined style={{ color: '#722ed1' }} />,
          color: '#722ed1',
          trend: 15.2,
        },
        {
          title: '本月入职',
          value: 23,
          icon: <UserAddOutlined style={{ color: '#52c41a' }} />,
          color: '#52c41a',
          suffix: '人',
          trend: 12.5,
        },
        {
          title: '待处理事项',
          value: 8,
          icon: <ClockCircleOutlined style={{ color: '#faad14' }} />,
          color: '#faad14',
          trend: -5.2,
        },
      ]);

      // 设置趋势数据
      setTrendData(mockTrendData);

      // 设置待办事项
      setTodoItems(mockTodoItems);

      setLoading(false);
    };

    loadData();
  }, []);

  // 处理待办事项点击
  const handleTodoClick = (item: TodoItem) => {
    console.log('Todo clicked:', item);
    // 导航到详情页或打开弹窗
  };

  // 处理待办事项完成
  const handleTodoComplete = (itemId: string) => {
    setTodoItems((prev) => prev.filter((item) => item.id !== itemId));
    console.log('Todo completed:', itemId);
  };

  return (
    <div style={{ padding: 24, background: '#f0f2f5', minHeight: 'calc(100vh - 64px - 69px)' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <Typography.Title level={4} style={{ marginBottom: 4 }}>
          工作台
        </Typography.Title>
        <Typography.Text type="secondary">
          欢迎回来！以下是您的招聘数据概览
        </Typography.Text>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statCards.map((stat, index) => (
          <Col xs={24} sm={12} lg={6} key={index}>
            <StatCardComponent stat={stat} />
          </Col>
        ))}
      </Row>

      {/* 趋势图 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <TrendChart data={trendData} />
        </Col>
      </Row>

      {/* 待办事项 */}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <TodoList items={todoItems} onItemClick={handleTodoClick} onComplete={handleTodoComplete} />
        </Col>
      </Row>
    </div>
  );
};

// ==================== 导出 ====================

export default Dashboard;
