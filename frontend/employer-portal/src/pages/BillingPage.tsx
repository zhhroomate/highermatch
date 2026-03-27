/**
 * HigherMatch™ Employer Portal - 账单中心页面
 * ============================================
 * 展示发票列表，支持模拟支付
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Typography,
  Space,
  Tag,
  Button,
  Modal,
  QRCode,
  Steps,
  message,
  Select,
  DatePicker,
  Input,
  Tooltip,
  Descriptions,
  Divider,
} from 'antd';
import {
  CreditCardOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  DownloadOutlined,
  SearchOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { apiClient } from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

/**
 * 账单数据类型
 */
export interface BillingRecord {
  id: string;
  jobTitle: string;
  candidateName: string;
  baseCommission: number;
  urgentPremium: number;
  totalAmount: number;
  status: 'pending' | 'paid' | 'overdue' | 'refunded';
  createdAt: string;
  dueDate: string;
  paidAt?: string;
  invoiceNo?: string;
}

/**
 * Mock 数据
 */
const generateMockBillingData = (): BillingRecord[] => [
  {
    id: 'b1',
    jobTitle: '高级后端工程师',
    candidateName: '张明',
    baseCommission: 15000,
    urgentPremium: 3000,
    totalAmount: 18000,
    status: 'paid',
    createdAt: '2024-03-01',
    dueDate: '2024-03-31',
    paidAt: '2024-03-15',
    invoiceNo: 'INV-2024-001',
  },
  {
    id: 'b2',
    jobTitle: '前端开发工程师',
    candidateName: '李华',
    baseCommission: 12000,
    urgentPremium: 0,
    totalAmount: 12000,
    status: 'pending',
    createdAt: '2024-03-10',
    dueDate: '2024-04-10',
  },
  {
    id: 'b3',
    jobTitle: '产品经理',
    candidateName: '王芳',
    baseCommission: 18000,
    urgentPremium: 5000,
    totalAmount: 23000,
    status: 'overdue',
    createdAt: '2024-02-15',
    dueDate: '2024-03-15',
  },
  {
    id: 'b4',
    jobTitle: 'UI设计师',
    candidateName: '赵伟',
    baseCommission: 10000,
    urgentPremium: 2000,
    totalAmount: 12000,
    status: 'pending',
    createdAt: '2024-03-18',
    dueDate: '2024-04-18',
  },
  {
    id: 'b5',
    jobTitle: '数据分析师',
    candidateName: '刘洋',
    baseCommission: 14000,
    urgentPremium: 0,
    totalAmount: 14000,
    status: 'refunded',
    createdAt: '2024-01-20',
    dueDate: '2024-02-20',
  },
  {
    id: 'b6',
    jobTitle: '运维工程师',
    candidateName: '陈静',
    baseCommission: 16000,
    urgentPremium: 4000,
    totalAmount: 20000,
    status: 'paid',
    createdAt: '2024-03-05',
    dueDate: '2024-04-05',
    paidAt: '2024-03-20',
    invoiceNo: 'INV-2024-002',
  },
];

/**
 * 账单中心页面
 */
const BillingPage: React.FC = () => {
  // 状态
  const [billingData, setBillingData] = useState<BillingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<BillingRecord | null>(null);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [paymentStep, setPaymentStep] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // 筛选状态
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [searchText, setSearchText] = useState('');

  // 统计数据
  const [stats, setStats] = useState({
    totalAmount: 0,
    pendingAmount: 0,
    paidAmount: 0,
    overdueAmount: 0,
  });

  // 加载数据
  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    setLoading(true);
    try {
      // TODO: 替换为实际 API 调用
      // const response = await apiClient.get('/api/v1/billing/list');
      // setBillingData(response.data);

      // 使用 Mock 数据
      const mockData = generateMockBillingData();
      setBillingData(mockData);

      // 计算统计
      const total = mockData.reduce((sum, r) => sum + r.totalAmount, 0);
      const pending = mockData.filter((r) => r.status === 'pending').reduce((sum, r) => sum + r.totalAmount, 0);
      const paid = mockData.filter((r) => r.status === 'paid').reduce((sum, r) => sum + r.totalAmount, 0);
      const overdue = mockData.filter((r) => r.status === 'overdue').reduce((sum, r) => sum + r.totalAmount, 0);

      setStats({ totalAmount: total, pendingAmount: pending, paidAmount: paid, overdueAmount: overdue });
    } catch (error) {
      console.error('加载账单失败:', error);
      message.error('加载账单数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 姓名脱敏
  const maskName = (name: string) => {
    if (name.length <= 1) return '*';
    return name.charAt(0) + '*'.repeat(name.length - 1);
  };

  // 格式化金额
  const formatAmount = (amount: number) => {
    return `¥${amount.toLocaleString()}`;
  };

  // 获取状态标签
  const getStatusTag = (status: BillingRecord['status']) => {
    switch (status) {
      case 'pending':
        return <Tag icon={<ClockCircleOutlined />} color="default">待支付</Tag>;
      case 'paid':
        return <Tag icon={<CheckCircleOutlined />} color="success">已支付</Tag>;
      case 'overdue':
        return <Tag icon={<ExclamationCircleOutlined />} color="error">已逾期</Tag>;
      case 'refunded':
        return <Tag icon={<CloseCircleOutlined />} color="warning">已退款</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  // 打开支付弹窗
  const handlePayClick = (record: BillingRecord) => {
    setSelectedRecord(record);
    setPaymentStep(0);
    setIsPaymentModalOpen(true);
  };

  // 模拟支付流程
  const handlePayment = async () => {
    setIsProcessing(true);

    // 模拟支付处理
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // 模拟支付成功
    setPaymentStep(1);

    // 2秒后更新状态
    setTimeout(async () => {
      try {
        // TODO: 调用实际支付接口
        // await apiClient.post(`/api/v1/billing/${selectedRecord?.id}/pay`);

        setBillingData((prev) =>
          prev.map((r) =>
            r.id === selectedRecord?.id
              ? { ...r, status: 'paid' as const, paidAt: new Date().toISOString().split('T')[0] }
              : r
          )
        );

        message.success('支付成功！');
        setIsPaymentModalOpen(false);
      } catch (error) {
        message.error('支付失败，请重试');
      } finally {
        setIsProcessing(false);
      }
    }, 2000);
  };

  // 关闭支付弹窗
  const handleModalClose = () => {
    setIsPaymentModalOpen(false);
    setSelectedRecord(null);
    setPaymentStep(0);
  };

  // 下载发票
  const handleDownloadInvoice = (record: BillingRecord) => {
    message.info(`正在下载发票 ${record.invoiceNo}...`);
    // TODO: 实现实际下载逻辑
  };

  // 表格列定义
  const columns: ColumnsType<BillingRecord> = [
    {
      title: '发票号',
      dataIndex: 'invoiceNo',
      key: 'invoiceNo',
      width: 150,
      render: (text, record) =>
        text || <Text type="secondary">-</Text>,
    },
    {
      title: '岗位名称',
      dataIndex: 'jobTitle',
      key: 'jobTitle',
      width: 180,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '候选人',
      dataIndex: 'candidateName',
      key: 'candidateName',
      width: 120,
      render: (text) => maskName(text),
    },
    {
      title: '基础佣金',
      dataIndex: 'baseCommission',
      key: 'baseCommission',
      width: 120,
      align: 'right',
      render: (amount) => (
        <Text style={{ color: '#666' }}>
          {formatAmount(amount)}
        </Text>
      ),
    },
    {
      title: '加急溢价',
      dataIndex: 'urgentPremium',
      key: 'urgentPremium',
      width: 120,
      align: 'right',
      render: (premium) => (
        <Text style={{ color: premium > 0 ? '#fa8c16' : '#999' }}>
          {premium > 0 ? `+${formatAmount(premium)}` : '-'}
        </Text>
      ),
    },
    {
      title: '总金额',
      dataIndex: 'totalAmount',
      key: 'totalAmount',
      width: 140,
      align: 'right',
      sorter: (a, b) => a.totalAmount - b.totalAmount,
      render: (amount, record) => (
        <Text strong style={{ fontSize: 16, color: '#1890ff' }}>
          {formatAmount(amount)}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => getStatusTag(status),
    },
    {
      title: '创建日期',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 120,
      render: (date) => date,
    },
    {
      title: '到期日期',
      dataIndex: 'dueDate',
      key: 'dueDate',
      width: 120,
      render: (date, record) => (
        <Text type={record.status === 'overdue' ? 'danger' : undefined}>
          {date}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {record.status === 'pending' && (
            <Button
              type="primary"
              size="small"
              icon={<CreditCardOutlined />}
              onClick={() => handlePayClick(record)}
            >
              立即支付
            </Button>
          )}
          {record.status === 'paid' && record.invoiceNo && (
            <Tooltip title="下载发票">
              <Button
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleDownloadInvoice(record)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // 筛选后的数据
  const filteredData = billingData.filter((record) => {
    const matchesStatus = !statusFilter || record.status === statusFilter;
    const matchesSearch =
      !searchText ||
      record.jobTitle.toLowerCase().includes(searchText.toLowerCase()) ||
      record.candidateName.toLowerCase().includes(searchText.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="billing-page" style={{ padding: 24 }}>
      {/* 页面标题 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>账单中心</Title>
          <Space>
            <Text type="secondary">共 {billingData.length} 条账单</Text>
          </Space>
        </div>
      </Card>

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 16 }}>
        <Card>
          <div style={{ textAlign: 'center' }}>
            <DollarOutlined style={{ fontSize: 24, color: '#1890ff', marginBottom: 8 }} />
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
              {formatAmount(stats.totalAmount)}
            </div>
            <Text type="secondary">账单总额</Text>
          </div>
        </Card>
        <Card>
          <div style={{ textAlign: 'center' }}>
            <ClockCircleOutlined style={{ fontSize: 24, color: '#fa8c16', marginBottom: 8 }} />
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fa8c16' }}>
              {formatAmount(stats.pendingAmount)}
            </div>
            <Text type="secondary">待支付</Text>
          </div>
        </Card>
        <Card>
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a', marginBottom: 8 }} />
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
              {formatAmount(stats.paidAmount)}
            </div>
            <Text type="secondary">已支付</Text>
          </div>
        </Card>
        <Card>
          <div style={{ textAlign: 'center' }}>
            <ExclamationCircleOutlined style={{ fontSize: 24, color: '#ff4d4f', marginBottom: 8 }} />
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
              {formatAmount(stats.overdueAmount)}
            </div>
            <Text type="secondary">已逾期</Text>
          </div>
        </Card>
      </div>

      {/* 筛选栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Space size="large" wrap>
          <Space>
            <Text>状态筛选:</Text>
            <Select
              placeholder="全部状态"
              style={{ width: 120 }}
              allowClear
              value={statusFilter}
              onChange={setStatusFilter}
            >
              <Option value="pending">待支付</Option>
              <Option value="paid">已支付</Option>
              <Option value="overdue">已逾期</Option>
              <Option value="refunded">已退款</Option>
            </Select>
          </Space>
          <Space>
            <Input
              placeholder="搜索岗位/候选人..."
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Space>
        </Space>
      </Card>

      {/* 账单列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredData}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* 支付弹窗 */}
      <Modal
        title="支付账单"
        open={isPaymentModalOpen}
        onCancel={handleModalClose}
        footer={null}
        width={500}
      >
        {selectedRecord && (
          <div>
            <Steps
              current={paymentStep}
              items={[
                { title: '确认订单' },
                { title: '扫码支付' },
                { title: '支付完成' },
              ]}
              style={{ marginBottom: 24 }}
            />

            {paymentStep === 0 && (
              <div>
                <Descriptions bordered column={1} style={{ marginBottom: 24 }}>
                  <Descriptions.Item label="岗位名称">
                    {selectedRecord.jobTitle}
                  </Descriptions.Item>
                  <Descriptions.Item label="候选人">
                    {maskName(selectedRecord.candidateName)}
                  </Descriptions.Item>
                  <Descriptions.Item label="基础佣金">
                    {formatAmount(selectedRecord.baseCommission)}
                  </Descriptions.Item>
                  <Descriptions.Item label="加急溢价">
                    {selectedRecord.urgentPremium > 0
                      ? formatAmount(selectedRecord.urgentPremium)
                      : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="总金额">
                    <Text strong style={{ fontSize: 18, color: '#1890ff' }}>
                      {formatAmount(selectedRecord.totalAmount)}
                    </Text>
                  </Descriptions.Item>
                </Descriptions>

                <Divider />

                <div style={{ textAlign: 'center' }}>
                  <Button
                    type="primary"
                    size="large"
                    onClick={() => setPaymentStep(1)}
                    block
                  >
                    确认并生成支付二维码
                  </Button>
                </div>
              </div>
            )}

            {paymentStep === 1 && (
              <div>
                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                  <QRCode
                    value={`https://sandbox.alipay.com/mock/${selectedRecord.id}`}
                    size={200}
                    style={{ marginBottom: 16 }}
                  />
                  <Title level={5}>请使用支付宝扫描二维码支付</Title>
                  <Text type="secondary">
                    支付金额：<Text strong style={{ color: '#1890ff', fontSize: 18 }}>
                      {formatAmount(selectedRecord.totalAmount)}
                    </Text>
                  </Text>
                </div>

                <div style={{ textAlign: 'center' }}>
                  <Button
                    type="primary"
                    size="large"
                    onClick={handlePayment}
                    loading={isProcessing}
                    block
                  >
                    {isProcessing ? '支付处理中...' : '我已支付'}
                  </Button>
                  <Button
                    type="link"
                    onClick={handleModalClose}
                    style={{ marginTop: 8 }}
                  >
                    取消
                  </Button>
                </div>
              </div>
            )}

            {paymentStep === 2 && (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <CheckCircleOutlined style={{ fontSize: 64, color: '#52c41a', marginBottom: 16 }} />
                <Title level={4}>支付成功！</Title>
                <Paragraph>
                  您的账单 <Text strong>{selectedRecord.invoiceNo || selectedRecord.id}</Text> 已支付成功。
                </Paragraph>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default BillingPage;
