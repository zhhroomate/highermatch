/**
 * HigherMatch™ Employer Portal - 入职与保障管理页面
 * ============================================
 * 展示入职候选人，保障期倒计时，申请保障补招
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Typography,
  Space,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Upload,
  Progress,
  message,
  Descriptions,
  Timeline,
  Tooltip,
  Row,
  Col,
  Badge,
  Divider,
  Empty,
} from 'antd';
import {
  UserAddOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
  FileTextOutlined,
  TeamOutlined,
  CalendarOutlined,
  SafetyCertificateOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { apiClient } from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

/**
 * 入职候选人数据类型
 */
export interface OnboardingCandidate {
  id: string;
  name: string;
  avatar?: string;
  jobTitle: string;
  jobId: string;
  department: string;
  position: string;
  hiredDate: string; // 入职日期
  guaranteeEndDate: string; // 保障期结束日期
  guaranteeDays: number; // 保障期总天数 (默认90)
  remainingDays: number; // 剩余天数
  status: 'active' | 'left' | 'guarantee_expired';
  monthlySalary: number; // 月薪
  commission: number; // 佣金
  contact: string;
  contactPhone: string;
  progressHistory: {
    date: string;
    title: string;
    description: string;
    type: 'milestone' | 'checkin' | 'issue';
  }[];
  documents: {
    name: string;
    url: string;
    uploadedAt: string;
  }[];
}

/**
 * Mock 数据
 */
const generateMockOnboardingData = (): OnboardingCandidate[] => {
  const today = new Date();

  return [
    {
      id: 'o1',
      name: '张明',
      avatar: 'https://i.pravatar.cc/150?img=1',
      jobTitle: '高级后端工程师',
      jobId: 'j1',
      department: '技术部',
      position: '高级工程师',
      hiredDate: new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeEndDate: new Date(today.getTime() + 60 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeDays: 90,
      remainingDays: 60,
      status: 'active',
      monthlySalary: 45000,
      commission: 18000,
      contact: 'zhangming@example.com',
      contactPhone: '138****1234',
      progressHistory: [
        { date: '2024-03-01', title: '正式入职', description: '张明正式入职技术部', type: 'milestone' },
        { date: '2024-03-15', title: '第一周签到', description: '完成第一周工作签到', type: 'checkin' },
        { date: '2024-03-22', title: '第一个月签到', description: '完成第一个月工作签到', type: 'checkin' },
      ],
      documents: [
        { name: '劳动合同.pdf', url: '/docs/contract1.pdf', uploadedAt: '2024-03-01' },
        { name: '离职证明.pdf', url: '/docs/resignation1.pdf', uploadedAt: '2024-02-28' },
      ],
    },
    {
      id: 'o2',
      name: '李华',
      avatar: 'https://i.pravatar.cc/150?img=2',
      jobTitle: '前端开发工程师',
      jobId: 'j2',
      department: '前端部',
      position: '中级工程师',
      hiredDate: new Date(today.getTime() - 75 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeEndDate: new Date(today.getTime() + 15 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeDays: 90,
      remainingDays: 15,
      status: 'active',
      monthlySalary: 30000,
      commission: 12000,
      contact: 'lihua@example.com',
      contactPhone: '139****5678',
      progressHistory: [
        { date: '2024-01-15', title: '正式入职', description: '李华正式入职前端部', type: 'milestone' },
        { date: '2024-01-29', title: '第一周签到', description: '完成第一周工作签到', type: 'checkin' },
        { date: '2024-02-12', title: '第一个月签到', description: '完成第一个月工作签到', type: 'checkin' },
        { date: '2024-02-26', title: '第二个月签到', description: '完成第二个月工作签到', type: 'checkin' },
      ],
      documents: [
        { name: '劳动合同.pdf', url: '/docs/contract2.pdf', uploadedAt: '2024-01-15' },
      ],
    },
    {
      id: 'o3',
      name: '王芳',
      avatar: 'https://i.pravatar.cc/150?img=3',
      jobTitle: '产品经理',
      jobId: 'j3',
      department: '产品部',
      position: '高级产品经理',
      hiredDate: new Date(today.getTime() - 95 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeEndDate: new Date(today.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeDays: 90,
      remainingDays: 0,
      status: 'guarantee_expired',
      monthlySalary: 50000,
      commission: 23000,
      contact: 'wangfang@example.com',
      contactPhone: '137****9012',
      progressHistory: [
        { date: '2023-12-25', title: '正式入职', description: '王芳正式入职产品部', type: 'milestone' },
        { date: '2024-01-08', title: '第一周签到', description: '完成第一周工作签到', type: 'checkin' },
        { date: '2024-01-22', title: '第一个月签到', description: '完成第一个月工作签到', type: 'checkin' },
        { date: '2024-02-05', title: '第二个月签到', description: '完成第二个月工作签到', type: 'checkin' },
        { date: '2024-02-19', title: '第三个月签到', description: '完成第三个月工作签到', type: 'checkin' },
      ],
      documents: [
        { name: '劳动合同.pdf', url: '/docs/contract3.pdf', uploadedAt: '2023-12-25' },
      ],
    },
    {
      id: 'o4',
      name: '赵伟',
      avatar: 'https://i.pravatar.cc/150?img=4',
      jobTitle: 'UI设计师',
      jobId: 'j4',
      department: '设计部',
      position: '资深设计师',
      hiredDate: new Date(today.getTime() - 45 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeEndDate: new Date(today.getTime() + 45 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeDays: 90,
      remainingDays: 45,
      status: 'active',
      monthlySalary: 35000,
      commission: 14000,
      contact: 'zhaowei@example.com',
      contactPhone: '136****3456',
      progressHistory: [
        { date: '2024-02-15', title: '正式入职', description: '赵伟正式入职设计部', type: 'milestone' },
        { date: '2024-03-01', title: '第一周签到', description: '完成第一周工作签到', type: 'checkin' },
      ],
      documents: [
        { name: '劳动合同.pdf', url: '/docs/contract4.pdf', uploadedAt: '2024-02-15' },
      ],
    },
    {
      id: 'o5',
      name: '刘洋',
      avatar: 'https://i.pravatar.cc/150?img=5',
      jobTitle: '运维工程师',
      jobId: 'j5',
      department: '运维部',
      position: '运维工程师',
      hiredDate: new Date(today.getTime() - 20 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeEndDate: new Date(today.getTime() + 70 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      guaranteeDays: 90,
      remainingDays: 70,
      status: 'active',
      monthlySalary: 40000,
      commission: 20000,
      contact: 'liuyang@example.com',
      contactPhone: '135****7890',
      progressHistory: [
        { date: '2024-03-10', title: '正式入职', description: '刘洋正式入职运维部', type: 'milestone' },
      ],
      documents: [],
    },
  ];
};

/**
 * 保障期倒计时进度条组件
 */
const GuaranteeProgress: React.FC<{
  remainingDays: number;
  totalDays: number;
  status: OnboardingCandidate['status'];
}> = ({ remainingDays, totalDays, status }) => {
  const percent = Math.max(0, Math.min(100, (remainingDays / totalDays) * 100));

  // 根据剩余天数计算颜色
  const getColor = () => {
    if (status === 'guarantee_expired') return '#999';
    if (percent > 50) return '#52c41a'; // 绿色
    if (percent > 25) return '#faad14'; // 黄色
    return '#ff4d4f'; // 红色
  };

  // 渐变色配置
  const gradientId = `progress-gradient-${Math.random().toString(36).substr(2, 9)}`;

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <Text type="secondary">保障期</Text>
        <Text strong style={{ color: getColor() }}>
          {status === 'guarantee_expired' ? '已过期' : `剩余 ${remainingDays} 天`}
        </Text>
      </div>
      <div style={{ position: 'relative', height: 8, background: '#f0f0f0', borderRadius: 4 }}>
        <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor={percent > 50 ? '#52c41a' : percent > 25 ? '#faad14' : '#ff4d4f'} />
              <stop offset="100%" stopColor={getColor()} />
            </linearGradient>
          </defs>
        </svg>
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: `${percent}%`,
            height: '100%',
            background: getColor(),
            borderRadius: 4,
            transition: 'width 0.3s ease, background-color 0.3s ease',
          }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <Text type="secondary" style={{ fontSize: 10 }}>入职</Text>
        <Text type="secondary" style={{ fontSize: 10 }}>保障期结束</Text>
      </div>
    </div>
  );
};

/**
 * 入职管理页面
 */
const OnboardingPage: React.FC = () => {
  // 状态
  const [candidates, setCandidates] = useState<OnboardingCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCandidate, setSelectedCandidate] = useState<OnboardingCandidate | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isGuaranteeModalOpen, setIsGuaranteeModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 表单
  const [form] = Form.useForm();

  // 统计数据
  const stats = useMemo(() => {
    return {
      total: candidates.length,
      active: candidates.filter((c) => c.status === 'active').length,
      expiringSoon: candidates.filter((c) => c.status === 'active' && c.remainingDays <= 15).length,
      expired: candidates.filter((c) => c.status === 'guarantee_expired').length,
    };
  }, [candidates]);

  // 加载数据
  useEffect(() => {
    loadCandidates();
  }, []);

  const loadCandidates = async () => {
    setLoading(true);
    try {
      // TODO: 替换为实际 API 调用
      // const response = await apiClient.get('/api/v1/onboarding/list');
      // setCandidates(response.data);

      // 使用 Mock 数据
      const mockData = generateMockOnboardingData();
      setCandidates(mockData);
    } catch (error) {
      console.error('加载数据失败:', error);
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 打开详情弹窗
  const handleViewDetail = (candidate: OnboardingCandidate) => {
    setSelectedCandidate(candidate);
    setIsDetailModalOpen(true);
  };

  // 打开保障申请弹窗
  const handleGuaranteeClick = (candidate: OnboardingCandidate) => {
    setSelectedCandidate(candidate);
    form.resetFields();
    setIsGuaranteeModalOpen(true);
  };

  // 提交保障申请
  const handleGuaranteeSubmit = async () => {
    try {
      const values = await form.validateFields();
      setIsSubmitting(true);

      // TODO: 替换为实际 API 调用
      // const response = await apiClient.post('/api/v1/guarantee/apply', {
      //   candidateId: selectedCandidate?.id,
      //   ...values,
      // });

      // 模拟提交
      await new Promise((resolve) => setTimeout(resolve, 1500));

      message.success('保障补招申请已提交，我们将在 24 小时内处理');
      setIsGuaranteeModalOpen(false);
    } catch (error) {
      console.error('提交失败:', error);
      message.error('提交失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 姓名脱敏
  const maskName = (name: string) => {
    if (name.length <= 1) return '*';
    return name.charAt(0) + '*'.repeat(name.length - 1);
  };

  // 上传文件
  const handleUpload = async (file: File) => {
    try {
      // TODO: 替换为实际文件上传
      // const formData = new FormData();
      // formData.append('file', file);
      // const response = await apiClient.post('/api/v1/upload', formData);

      // 模拟上传
      await new Promise((resolve) => setTimeout(resolve, 1000));
      message.success(`${file.name} 上传成功`);
      return false; // 阻止默认上传
    } catch (error) {
      message.error('上传失败');
      return false;
    }
  };

  // 渲染候选人卡片
  const renderCandidateCard = (candidate: OnboardingCandidate) => {
    return (
      <Card
        key={candidate.id}
        hoverable
        style={{ height: '100%' }}
        styles={{ body: { padding: 16 } }}
      >
        {/* 卡片头部 */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <img
            src={candidate.avatar}
            alt={candidate.name}
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              objectFit: 'cover',
            }}
          />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text strong style={{ fontSize: 16 }}>{maskName(candidate.name)}</Text>
              {candidate.status === 'guarantee_expired' && (
                <Tag color="default" icon={<ClockCircleOutlined />}>保障已过期</Tag>
              )}
              {candidate.status === 'active' && candidate.remainingDays <= 15 && (
                <Tag color="warning" icon={<WarningOutlined />}>即将到期</Tag>
              )}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>{candidate.jobTitle}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {candidate.department} · {candidate.position}
            </Text>
          </div>
        </div>

        {/* 保障期进度 */}
        <GuaranteeProgress
          remainingDays={candidate.remainingDays}
          totalDays={candidate.guaranteeDays}
          status={candidate.status}
        />

        <Divider style={{ margin: '12px 0' }} />

        {/* 基本信息 */}
        <div style={{ marginBottom: 12 }}>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Space size={4}>
                <CalendarOutlined style={{ color: '#999' }} />
                <Text type="secondary" style={{ fontSize: 12 }}>入职日期</Text>
              </Space>
              <br />
              <Text style={{ fontSize: 12 }}>{candidate.hiredDate}</Text>
            </Col>
            <Col span={12}>
              <Space size={4}>
                <TeamOutlined style={{ color: '#999' }} />
                <Text type="secondary" style={{ fontSize: 12 }}>月薪</Text>
              </Space>
              <br />
              <Text style={{ fontSize: 12, color: '#1890ff' }}>
                ¥{candidate.monthlySalary.toLocaleString()}
              </Text>
            </Col>
          </Row>
        </div>

        {/* 操作按钮 */}
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            type="primary"
            ghost
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => handleViewDetail(candidate)}
            style={{ flex: 1 }}
          >
            查看详情
          </Button>
          {(candidate.status === 'active' || candidate.status === 'guarantee_expired') && (
            <Button
              type="primary"
              size="small"
              danger
              icon={<SafetyCertificateOutlined />}
              onClick={() => handleGuaranteeClick(candidate)}
            >
              申请补招
            </Button>
          )}
        </div>
      </Card>
    );
  };

  return (
    <div className="onboarding-page" style={{ padding: 24 }}>
      {/* 页面标题 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>入职与保障管理</Title>
          <Space>
            <Badge count={stats.total} style={{ backgroundColor: '#1890ff' }}>
              <Text>在职候选人</Text>
            </Badge>
          </Space>
        </div>
      </Card>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <TeamOutlined style={{ fontSize: 24, color: '#1890ff', marginBottom: 8 }} />
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>{stats.total}</div>
              <Text type="secondary">在职总数</Text>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a', marginBottom: 8 }} />
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>{stats.active}</div>
              <Text type="secondary">保障期内</Text>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <WarningOutlined style={{ fontSize: 24, color: '#faad14', marginBottom: 8 }} />
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>{stats.expiringSoon}</div>
              <Text type="secondary">即将到期</Text>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ textAlign: 'center' }}>
              <ClockCircleOutlined style={{ fontSize: 24, color: '#999', marginBottom: 8 }} />
              <div style={{ fontSize: 24, fontWeight: 'bold', color: '#999' }}>{stats.expired}</div>
              <Text type="secondary">已过期</Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 候选人列表 */}
      <Row gutter={[16, 16]}>
        {candidates.map((candidate) => (
          <Col key={candidate.id} xs={24} sm={12} lg={8} xl={6}>
            {renderCandidateCard(candidate)}
          </Col>
        ))}
      </Row>

      {candidates.length === 0 && !loading && (
        <Empty description="暂无入职候选人" style={{ marginTop: 60 }} />
      )}

      {/* 详情弹窗 */}
      <Modal
        title="候选人详情"
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={700}
      >
        {selectedCandidate && (
          <div>
            {/* 基本信息 */}
            <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="姓名" span={2}>
                <Space>
                  <img
                    src={selectedCandidate.avatar}
                    alt={selectedCandidate.name}
                    style={{ width: 40, height: 40, borderRadius: '50%' }}
                  />
                  <Text strong>{maskName(selectedCandidate.name)}</Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="岗位">{selectedCandidate.jobTitle}</Descriptions.Item>
              <Descriptions.Item label="部门">{selectedCandidate.department}</Descriptions.Item>
              <Descriptions.Item label="职位">{selectedCandidate.position}</Descriptions.Item>
              <Descriptions.Item label="月薪">¥{selectedCandidate.monthlySalary.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="佣金">¥{selectedCandidate.commission.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="入职日期">{selectedCandidate.hiredDate}</Descriptions.Item>
              <Descriptions.Item label="保障期结束">{selectedCandidate.guaranteeEndDate}</Descriptions.Item>
              <Descriptions.Item label="联系方式" span={2}>{selectedCandidate.contact}</Descriptions.Item>
            </Descriptions>

            {/* 保障期进度 */}
            <Card title="保障期状态" style={{ marginBottom: 24 }}>
              <GuaranteeProgress
                remainingDays={selectedCandidate.remainingDays}
                totalDays={selectedCandidate.guaranteeDays}
                status={selectedCandidate.status}
              />
              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <Text type="secondary">
                  已过 {selectedCandidate.guaranteeDays - selectedCandidate.remainingDays} 天，
                  剩余 {selectedCandidate.remainingDays} 天保障期
                </Text>
              </div>
            </Card>

            {/* 进度历史 */}
            <Card title="入职进度" style={{ marginBottom: 24 }}>
              <Timeline
                items={selectedCandidate.progressHistory.map((item) => ({
                  color: item.type === 'milestone' ? 'blue' : item.type === 'issue' ? 'red' : 'green',
                  children: (
                    <div>
                      <Text strong>{item.title}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>{item.description}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 10 }}>{item.date}</Text>
                    </div>
                  ),
                }))}
              />
            </Card>

            {/* 文档列表 */}
            {selectedCandidate.documents.length > 0 && (
              <Card title="相关文档">
                {selectedCandidate.documents.map((doc, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '8px 0',
                      borderBottom: idx < selectedCandidate.documents.length - 1 ? '1px solid #f0f0f0' : 'none',
                    }}
                  >
                    <Space>
                      <FileTextOutlined />
                      <Text>{doc.name}</Text>
                    </Space>
                    <Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>{doc.uploadedAt}</Text>
                      <Button type="link" size="small" icon={<UploadOutlined />}>
                        下载
                      </Button>
                    </Space>
                  </div>
                ))}
              </Card>
            )}
          </div>
        )}
      </Modal>

      {/* 保障补招申请弹窗 */}
      <Modal
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>申请保障补招</span>
          </Space>
        }
        open={isGuaranteeModalOpen}
        onCancel={() => setIsGuaranteeModalOpen(false)}
        footer={[
          <Button key="cancel" onClick={() => setIsGuaranteeModalOpen(false)}>
            取消
          </Button>,
          <Button
            key="submit"
            type="primary"
            danger
            loading={isSubmitting}
            onClick={handleGuaranteeSubmit}
          >
            提交申请
          </Button>,
        ]}
        width={600}
      >
        {selectedCandidate && (
          <Form form={form} layout="vertical">
            {/* 候选人信息 */}
            <Card style={{ marginBottom: 16, background: '#fafafa' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Text type="secondary">候选人</Text>
                  <br />
                  <Text strong>{maskName(selectedCandidate.name)}</Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">岗位</Text>
                  <br />
                  <Text strong>{selectedCandidate.jobTitle}</Text>
                </Col>
              </Row>
            </Card>

            <Alert
              message="保障说明"
              description="若候选人在90天保障期内离职，我们将免费为您推荐一名同等水平的候选人。"
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              name="reason"
              label="离职原因"
              rules={[{ required: true, message: '请填写离职原因' }]}
            >
              <TextArea
                rows={4}
                placeholder="请详细描述候选人离职的原因..."
                maxLength={500}
                showCount
              />
            </Form.Item>

            <Form.Item
              name="department"
              label="部门确认"
              rules={[{ required: true, message: '请选择确认部门' }]}
            >
              <Select placeholder="请选择确认部门">
                <Option value={selectedCandidate.department}>{selectedCandidate.department}</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="files"
              label="证明文件"
              extra="支持上传劳动合同、离职证明、聊天记录等（可选）"
            >
              <Upload.Dragger
                name="files"
                multiple
                beforeUpload={handleUpload}
                fileList={[]}
              >
                <p className="ant-upload-drag-icon">
                  <UploadOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                <p className="ant-upload-hint">支持 PDF、Word、图片格式，单个文件不超过 10MB</p>
              </Upload.Dragger>
            </Form.Item>

            <Form.Item name="remark" label="备注">
              <TextArea
                rows={2}
                placeholder="如有其他补充说明，请在此填写..."
                maxLength={200}
              />
            </Form.Item>
          </Form>
        )}
      </Modal>

      {/* 导入 Alert 组件 */}
      <style>{`
        .ant-upload-drag {
          border-color: #d9d9d9 !important;
        }
        .ant-upload-drag:hover {
          border-color: #1890ff !important;
        }
      `}</style>
    </div>
  );
};

// 添加 Alert 组件导入
import { Alert } from 'antd';

export default OnboardingPage;
