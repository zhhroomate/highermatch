/**
 * HigherMatch™ Employer Portal - 职位管理页面
 * ==========================================
 *
 * 版本: 1.0.0
 */

import React from 'react';
import { Typography, Table, Button, Tag, Space, Card, Input } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

/**
 * 职位管理页面
 */
const Jobs: React.FC = () => {
  const columns = [
    {
      title: '职位名称',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <a>{text}</a>,
    },
    {
      title: '工作地点',
      dataIndex: 'location',
      key: 'location',
    },
    {
      title: '薪资范围',
      dataIndex: 'salary',
      key: 'salary',
      render: (salary: string) => <span style={{ color: '#52c41a' }}>{salary}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          active: 'green',
          paused: 'orange',
          closed: 'red',
        };
        const labels: Record<string, string> = {
          active: '招聘中',
          paused: '已暂停',
          closed: '已关闭',
        };
        return <Tag color={colors[status]}>{labels[status]}</Tag>;
      },
    },
    {
      title: '收到简历',
      dataIndex: 'applications',
      key: 'applications',
    },
    {
      title: '匹配候选人',
      dataIndex: 'matches',
      key: 'matches',
    },
    {
      title: '发布时间',
      dataIndex: 'publishedAt',
      key: 'publishedAt',
    },
    {
      title: '操作',
      key: 'action',
      render: () => (
        <Space size="small">
          <Button type="link" size="small">
            编辑
          </Button>
          <Button type="link" size="small" danger>
            关闭
          </Button>
        </Space>
      ),
    },
  ];

  const data = [
    {
      key: '1',
      title: 'Python 后端工程师',
      location: '北京',
      salary: '25K-45K',
      status: 'active',
      applications: 128,
      matches: 45,
      publishedAt: '2024-01-15',
    },
    {
      key: '2',
      title: '高级 Java 工程师',
      location: '上海',
      salary: '35K-60K',
      status: 'active',
      applications: 89,
      matches: 32,
      publishedAt: '2024-01-10',
    },
    {
      key: '3',
      title: '产品经理',
      location: '深圳',
      salary: '30K-50K',
      status: 'paused',
      applications: 56,
      matches: 18,
      publishedAt: '2024-01-05',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>职位管理</Title>
          <Text type="secondary">管理您的招聘信息</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />}>
          发布新职位
        </Button>
      </div>

      <Card bordered={false} style={{ borderRadius: 12 }}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Input placeholder="搜索职位名称..." prefix={<SearchOutlined />} />
            <Button>筛选</Button>
          </Space>
        </div>
        <Table columns={columns} dataSource={data} pagination={false} />
      </Card>
    </div>
  );
};

export default Jobs;
