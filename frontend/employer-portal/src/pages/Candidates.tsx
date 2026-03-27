/**
 * HigherMatch™ Employer Portal - 候选人页面
 * ==========================================
 *
 * 版本: 1.0.0
 */

import React from 'react';
import { Typography, Table, Button, Tag, Space, Avatar, Card, Input } from 'antd';
import { SearchOutlined, UserOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

/**
 * 候选人页面
 */
const Candidates: React.FC = () => {
  const columns = [
    {
      title: '候选人',
      key: 'candidate',
      render: (_: any, record: any) => (
        <Space>
          <Avatar icon={<UserOutlined />} src={record.avatar} />
          <div>
            <div>{record.name}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>{record.email}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: '当前职位',
      dataIndex: 'currentTitle',
      key: 'currentTitle',
    },
    {
      title: '期望职位',
      dataIndex: 'expectedTitle',
      key: 'expectedTitle',
    },
    {
      title: '期望薪资',
      dataIndex: 'expectedSalary',
      key: 'expectedSalary',
      render: (salary: string) => <span style={{ color: '#52c41a' }}>{salary}</span>,
    },
    {
      title: '匹配度',
      dataIndex: 'matchScore',
      key: 'matchScore',
      render: (score: number) => (
        <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red'}>
          {score}%
        </Tag>
      ),
    },
    {
      title: '求职状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          active: 'green',
          passive: 'blue',
          urgent: 'red',
        };
        const labels: Record<string, string> = {
          active: '积极求职',
          passive: '观望中',
          urgent: '急找工作',
        };
        return <Tag color={colors[status]}>{labels[status]}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space size="small">
          <Button type="link" size="small">
            查看
          </Button>
          <Button type="link" size="small">
            收藏
          </Button>
        </Space>
      ),
    },
  ];

  const data = [
    {
      key: '1',
      name: '张三',
      email: 'zhangsan@example.com',
      avatar: null,
      currentTitle: 'Python 开发工程师',
      expectedTitle: 'Python 后端工程师',
      expectedSalary: '30K-45K',
      matchScore: 92,
      status: 'active',
    },
    {
      key: '2',
      name: '李四',
      email: 'lisi@example.com',
      avatar: null,
      currentTitle: 'Java 高级工程师',
      expectedTitle: 'Java 技术专家',
      expectedSalary: '45K-60K',
      matchScore: 87,
      status: 'passive',
    },
    {
      key: '3',
      name: '王五',
      email: 'wangwu@example.com',
      avatar: null,
      currentTitle: '产品经理',
      expectedTitle: '高级产品经理',
      expectedSalary: '35K-50K',
      matchScore: 78,
      status: 'urgent',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>候选人库</Title>
          <Text type="secondary">浏览和管理候选人</Text>
        </div>
        <Space>
          <Input placeholder="搜索候选人..." prefix={<SearchOutlined />} style={{ width: 200 }} />
          <Button>高级筛选</Button>
        </Space>
      </div>

      <Card bordered={false} style={{ borderRadius: 12 }}>
        <Table columns={columns} dataSource={data} pagination={{ pageSize: 10 }} />
      </Card>
    </div>
  );
};

export default Candidates;
