/**
 * HigherMatch™ Employer Portal - AI理解确认卡片
 * ============================================
 * 展示 AI 提取的字段，支持置信度提示和追问交互
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Input,
  Tag,
  Space,
  Button,
  Divider,
  Badge,
  Tooltip,
  Collapse,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  MessageOutlined,
  EditOutlined,
  EyeOutlined,
  RobotOutlined,
  UserOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Panel } = Collapse;

/**
 * 字段数据类型
 */
export interface NluField {
  key: string;
  label: string;
  value: string;
  confidence: number; // 0-1
  suggestions?: string[];
  originalText?: string;
}

/**
 * AI 追问数据类型
 */
export interface NluFollowUp {
  fieldKey: string;
  question: string;
  userAnswer?: string;
}

/**
 * NluConfirmCard 属性
 */
interface NluConfirmCardProps {
  fields: NluField[];
  originalText: string;
  followUps?: NluFollowUp[];
  onFieldUpdate?: (fieldKey: string, value: string) => void;
  onFollowUpAnswer?: (fieldKey: string, answer: string) => void;
  onConfirm?: (confirmedFields: NluField[]) => void;
  loading?: boolean;
}

/**
 * AI 理解确认卡片组件
 */
const NluConfirmCard: React.FC<NluConfirmCardProps> = ({
  fields,
  originalText,
  followUps = [],
  onFieldUpdate,
  onFollowUpAnswer,
  onConfirm,
  loading = false,
}) => {
  // 本地编辑状态
  const [editedFields, setEditedFields] = useState<Record<string, string>>({});
  const [followUpAnswers, setFollowUpAnswers] = useState<Record<string, string>>({});
  const [editingField, setEditingField] = useState<string | null>(null);
  const [confirmedFields, setConfirmedFields] = useState<Set<string>>(new Set());

  // 初始化编辑状态
  useEffect(() => {
    const initial: Record<string, string> = {};
    fields.forEach((f) => {
      initial[f.key] = f.value;
    });
    setEditedFields(initial);
  }, [fields]);

  // 处理字段编辑
  const handleFieldEdit = (fieldKey: string, value: string) => {
    setEditedFields((prev) => ({ ...prev, [fieldKey]: value }));
    setEditingField(null);

    if (onFieldUpdate) {
      onFieldUpdate(fieldKey, value);
    }
  };

  // 处理追问回答
  const handleFollowUpAnswer = (fieldKey: string, answer: string) => {
    setFollowUpAnswers((prev) => ({ ...prev, [fieldKey]: answer }));

    if (onFollowUpAnswer) {
      onFollowUpAnswer(fieldKey, answer);
    }
  };

  // 确认字段
  const handleConfirmField = (fieldKey: string) => {
    setConfirmedFields((prev) => new Set([...prev, fieldKey]));
  };

  // 全部确认
  const handleConfirmAll = () => {
    fields.forEach((f) => {
      if (f.confidence >= 0.8) {
        setConfirmedFields((prev) => new Set([...prev, f.key]));
      }
    });

    if (onConfirm) {
      const confirmed = fields.map((f) => ({
        ...f,
        value: editedFields[f.key] || f.value,
      }));
      onConfirm(confirmed);
    }
  };

  // 获取置信度标签
  const getConfidenceTag = (confidence: number) => {
    if (confidence >= 0.9) {
      return <Tag color="green" icon={<CheckCircleOutlined />}>高置信度</Tag>;
    } else if (confidence >= 0.8) {
      return <Tag color="cyan">中等置信度</Tag>;
    } else if (confidence >= 0.6) {
      return <Tag color="orange" icon={<WarningOutlined />}>需确认</Tag>;
    } else {
      return <Tag color="red" icon={<WarningOutlined />}>低置信度</Tag>;
    }
  };

  // 获取追问气泡
  const getFollowUp = (fieldKey: string) => {
    return followUps.find((f) => f.fieldKey === fieldKey);
  };

  return (
    <div className="nlu-confirm-card" style={{ width: '100%' }}>
      {/* 双栏布局 */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 24,
        }}
      >
        {/* 左侧：AI 提取的字段 */}
        <Card
          title={
            <Space>
              <RobotOutlined />
              <span>AI 提取的信息</span>
            </Space>
          }
          extra={
            <Tag color="blue">
              {fields.length} 个字段
            </Tag>
          }
          styles={{ body: { padding: 16 } }}
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {fields.map((field) => {
              const isLowConfidence = field.confidence < 0.8;
              const isEditing = editingField === field.key;
              const isConfirmed = confirmedFields.has(field.key);
              const followUp = getFollowUp(field.key);

              return (
                <div
                  key={field.key}
                  style={{
                    padding: 16,
                    borderRadius: 8,
                    background: isLowConfidence ? '#fffbe6' : '#f6ffed',
                    border: `1px solid ${isLowConfidence ? '#ffe58f' : '#b7eb8f'}`,
                    position: 'relative',
                  }}
                >
                  {/* 字段头部 */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: 8,
                    }}
                  >
                    <Space>
                      <Text strong style={{ color: '#1890ff' }}>
                        {field.label}
                      </Text>
                      {getConfidenceTag(field.confidence)}
                    </Space>

                    {isConfirmed ? (
                      <Tag color="success" icon={<CheckCircleOutlined />}>
                        已确认
                      </Tag>
                    ) : isLowConfidence ? (
                      <Tooltip title="点击确认此字段">
                        <Button
                          type="link"
                          size="small"
                          icon={<CheckCircleOutlined />}
                          onClick={() => handleConfirmField(field.key)}
                        >
                          确认
                        </Button>
                      </Tooltip>
                    ) : null}
                  </div>

                  {/* 字段值 */}
                  {isEditing ? (
                    <div>
                      <Input.TextArea
                        value={editedFields[field.key]}
                        onChange={(e) =>
                          setEditedFields((prev) => ({
                            ...prev,
                            [field.key]: e.target.value,
                          }))
                        }
                        autoSize={{ minRows: 2, maxRows: 4 }}
                        style={{ marginBottom: 8 }}
                      />
                      <Space>
                        <Button
                          type="primary"
                          size="small"
                          onClick={() => handleFieldEdit(field.key, editedFields[field.key])}
                        >
                          保存
                        </Button>
                        <Button size="small" onClick={() => setEditingField(null)}>
                          取消
                        </Button>
                      </Space>
                    </div>
                  ) : (
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                      }}
                    >
                      <Text style={{ fontSize: 15, flex: 1 }}>{editedFields[field.key]}</Text>
                      <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => setEditingField(field.key)}
                      >
                        编辑
                      </Button>
                    </div>
                  )}

                  {/* 建议值 */}
                  {field.suggestions && field.suggestions.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        建议值：
                      </Text>
                      <Space size={4} style={{ marginTop: 4 }}>
                        {field.suggestions.slice(0, 3).map((s, idx) => (
                          <Tag
                            key={idx}
                            style={{ cursor: 'pointer' }}
                            onClick={() => handleFieldEdit(field.key, s)}
                          >
                            {s}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  )}

                  {/* AI 追问气泡 */}
                  {followUp && !followUp.userAnswer && (
                    <div
                      style={{
                        marginTop: 12,
                        padding: 12,
                        borderRadius: 8,
                        background: '#e6f7ff',
                        border: '1px solid #91d5ff',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <Badge count={<MessageOutlined />} style={{ backgroundColor: '#1890ff' }}>
                          <div />
                        </Badge>
                        <div style={{ flex: 1 }}>
                          <Text style={{ fontSize: 13, color: '#1890ff' }}>
                            {followUp.question}
                          </Text>
                          <Input
                            placeholder="请输入您的回答..."
                            value={followUpAnswers[field.key] || ''}
                            onChange={(e) =>
                              handleFollowUpAnswer(field.key, e.target.value)
                            }
                            style={{ marginTop: 8 }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 已回答的追问 */}
                  {followUp && followUp.userAnswer && (
                    <div
                      style={{
                        marginTop: 12,
                        padding: 12,
                        borderRadius: 8,
                        background: '#f6ffed',
                        border: '1px solid #b7eb8f',
                      }}
                    >
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        您的回答：
                      </Text>
                      <Paragraph style={{ marginTop: 4, marginBottom: 0 }}>
                        {followUp.userAnswer}
                      </Paragraph>
                    </div>
                  )}
                </div>
              );
            })}
          </Space>

          {/* 底部操作 */}
          <Divider />
          <div style={{ textAlign: 'center' }}>
            <Space>
              <Button
                type="primary"
                size="large"
                icon={<CheckCircleOutlined />}
                onClick={handleConfirmAll}
                loading={loading}
              >
                确认并继续
              </Button>
            </Space>
          </div>
        </Card>

        {/* 右侧：原始输入 */}
        <Card
          title={
            <Space>
              <EyeOutlined />
              <span>原始输入</span>
            </Space>
          }
          styles={{ body: { padding: 16 } }}
        >
          <div
            style={{
              padding: 16,
              background: '#fafafa',
              borderRadius: 8,
              border: '1px solid #d9d9d9',
              maxHeight: 400,
              overflow: 'auto',
            }}
          >
            <Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
              {originalText || '暂无原始输入'}
            </Paragraph>
          </div>

          {/* 统计信息 */}
          <div style={{ marginTop: 16 }}>
            <Collapse ghost>
              <Panel header="详细信息" key="details">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">总字段数</Text>
                    <Text>{fields.length}</Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">高置信度</Text>
                    <Text style={{ color: '#52c41a' }}>
                      {fields.filter((f) => f.confidence >= 0.9).length}
                    </Text>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text type="secondary">需确认</Text>
                    <Text style={{ color: '#faad14' }}>
                      {fields.filter((f) => f.confidence < 0.8).length}
                    </Text>
                  </div>
                </Space>
              </Panel>
            </Collapse>
          </div>
        </Card>
      </div>

      {/* 响应式布局 */}
      <style>{`
        @media (max-width: 768px) {
          .nlu-confirm-card > div {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};

export default NluConfirmCard;
