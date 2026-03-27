/**
 * HigherMatch™ Employer Portal - 新建职位页面
 * ============================================
 * 整合语音录入和 AI 理解确认功能
 *
 * 版本: 1.0.0
 */

import React, { useState, useCallback } from 'react';
import {
  Card,
  Steps,
  Button,
  Typography,
  Space,
  Input,
  Select,
  Form,
  Divider,
  message,
  Modal,
  Tag,
  Row,
  Col,
  Spin,
  Result,
  Tabs,
  Alert,
  Descriptions,
} from 'antd';
import {
  AudioOutlined,
  RobotOutlined,
  SendOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  SaveOutlined,
  UploadOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import VoiceRecorder from '../components/VoiceRecorder';
import NluConfirmCard, { NluField, NluFollowUp } from '../components/NluConfirmCard';
import { apiClient } from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

/**
 * 步骤状态
 */
type StepStatus = 'wait' | 'process' | 'finish' | 'error';

/**
 * 职位数据
 */
interface JobFormData {
  title: string;
  description: string;
  requirements: string[];
  salaryMin: number;
  salaryMax: number;
  location: string;
  jobType: string;
  experienceLevel: string;
  skills: string[];
}

/**
 * NLU 处理结果
 */
interface NluResult {
  fields: NluField[];
  followUps: NluFollowUp[];
  summary: string;
}

const { Search } = Input;

/**
 * 新建职位页面
 */
const NewJobPage: React.FC = () => {
  const navigate = useNavigate();

  // 步骤状态
  const [currentStep, setCurrentStep] = useState(0);
  const [stepStatuses, setStepStatuses] = useState<StepStatus[]>(['process', 'wait', 'wait', 'wait']);

  // 语音录入的文本
  const [voiceText, setVoiceText] = useState('');
  const [manualText, setManualText] = useState('');

  // NLU 处理状态
  const [isProcessingNlu, setIsProcessingNlu] = useState(false);
  const [nluResult, setNluResult] = useState<NluResult | null>(null);

  // 职位表单数据
  const [formData, setFormData] = useState<JobFormData>({
    title: '',
    description: '',
    requirements: [],
    salaryMin: 0,
    salaryMax: 0,
    location: '',
    jobType: 'full-time',
    experienceLevel: 'mid',
    skills: [],
  });

  // 提交状态
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  // 技能选项
  const skillOptions = [
    'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'C++',
    'React', 'Vue', 'Angular', 'Node.js', 'Spring Boot', 'Django',
    'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Kafka',
    'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
    'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
    'Agile/Scrum', 'Project Management', 'Leadership',
  ];

  // 城市选项
  const cityOptions = [
    '北京', '上海', '深圳', '广州', '杭州', '成都', '南京',
    '苏州', '武汉', '西安', '厦门', '长沙', '天津', '重庆',
  ];

  // 处理语音转写完成
  const handleTranscriptionComplete = useCallback((text: string) => {
    setVoiceText(text);
    setManualText(text);
  }, []);

  // 跳转到下一步
  const goToNextStep = () => {
    if (currentStep === 0 && !manualText) {
      message.warning('请先录入职位需求');
      return;
    }

    const newStatuses = [...stepStatuses];
    newStatuses[currentStep] = 'finish';
    if (currentStep + 1 < newStatuses.length) {
      newStatuses[currentStep + 1] = 'process';
    }
    setStepStatuses(newStatuses);

    if (currentStep === 0) {
      // 开始 NLU 处理
      handleNluProcess();
    } else {
      setCurrentStep((prev) => prev + 1);
    }
  };

  // 跳转到上一步
  const goToPrevStep = () => {
    const newStatuses = [...stepStatuses];
    newStatuses[currentStep] = 'wait';
    if (currentStep > 0) {
      newStatuses[currentStep - 1] = 'process';
    }
    setStepStatuses(newStatuses);
    setCurrentStep((prev) => prev - 1);
  };

  // NLU 处理
  const handleNluProcess = async () => {
    setIsProcessingNlu(true);

    try {
      // 调用 NLU 接口
      const response = await apiClient.post<NluResult>('/api/v1/nlu/extract', {
        text: manualText,
        type: 'job_requirements',
      });

      setNluResult(response);

      // 如果有提取的字段，自动填充表单
      const titleField = response.fields.find((f) => f.key === 'title');
      const descField = response.fields.find((f) => f.key === 'description');
      const skillsField = response.fields.find((f) => f.key === 'skills');
      const salaryMinField = response.fields.find((f) => f.key === 'salaryMin');
      const salaryMaxField = response.fields.find((f) => f.key === 'salaryMax');
      const locationField = response.fields.find((f) => f.key === 'location');

      setFormData((prev) => ({
        ...prev,
        title: titleField?.value || prev.title,
        description: descField?.value || prev.description,
        skills: skillsField?.value ? skillsField.value.split(',').map((s: string) => s.trim()) : prev.skills,
        salaryMin: salaryMinField?.value ? parseInt(salaryMinField.value) : prev.salaryMin,
        salaryMax: salaryMaxField?.value ? parseInt(salaryMaxField.value) : prev.salaryMax,
        location: locationField?.value || prev.location,
      }));

      setCurrentStep(1);
      message.success('AI 分析完成');
    } catch (error) {
      console.error('NLU 处理失败:', error);
      message.error('AI 分析失败，请手动填写');

      // 模拟 NLU 结果用于演示
      setNluResult({
        fields: [
          { key: 'title', label: '职位名称', value: '高级后端工程师', confidence: 0.95 },
          { key: 'description', label: '职位描述', value: manualText, confidence: 0.92 },
          { key: 'skills', label: '技能要求', value: 'Python, Go, PostgreSQL', confidence: 0.88 },
          { key: 'salaryMin', label: '最低薪资', value: '30000', confidence: 0.85 },
          { key: 'salaryMax', label: '最高薪资', value: '50000', confidence: 0.85 },
          { key: 'location', label: '工作地点', value: '北京', confidence: 0.98 },
        ],
        followUps: [
          { fieldKey: 'experienceLevel', question: '请问该职位的最低工作年限要求是？' },
        ],
        summary: '这是一份高级后端工程师职位，主要使用 Python/Go 开发，需要有 PostgreSQL 经验。',
      });

      setCurrentStep(1);
    } finally {
      setIsProcessingNlu(false);
    }
  };

  // 处理 NLU 确认
  const handleNluConfirm = (confirmedFields: NluField[]) => {
    confirmedFields.forEach((field) => {
      setFormData((prev) => {
        switch (field.key) {
          case 'title':
            return { ...prev, title: field.value };
          case 'description':
            return { ...prev, description: field.value };
          case 'skills':
            return { ...prev, skills: field.value.split(',').map((s) => s.trim()) };
          case 'salaryMin':
            return { ...prev, salaryMin: parseInt(field.value) || 0 };
          case 'salaryMax':
            return { ...prev, salaryMax: parseInt(field.value) || 0 };
          case 'location':
            return { ...prev, location: field.value };
          default:
            return prev;
        }
      });
    });

    goToNextStep();
  };

  // 处理字段更新
  const handleFieldUpdate = (fieldKey: string, value: string) => {
    console.log(`字段 ${fieldKey} 更新为: ${value}`);
  };

  // 处理追问回答
  const handleFollowUpAnswer = (fieldKey: string, answer: string) => {
    const expLevel = fieldKey === 'experienceLevel' ? answer : formData.experienceLevel;
    setFormData((prev) => ({
      ...prev,
      experienceLevel: expLevel,
    }));
  };

  // 处理表单提交
  const handleSubmit = async () => {
    setIsSubmitting(true);

    try {
      const response = await apiClient.post('/api/v1/jobs', formData);
      message.success('职位发布成功！');
      setIsSubmitted(true);
    } catch (error) {
      console.error('发布失败:', error);
      message.error('发布失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 步骤配置
  const steps = [
    {
      title: '录入需求',
      icon: <AudioOutlined />,
    },
    {
      title: 'AI 确认',
      icon: <RobotOutlined />,
    },
    {
      title: '完善信息',
      icon: <EditOutlined />,
    },
    {
      title: '确认发布',
      icon: <SendOutlined />,
    },
  ];

  // 重新编辑按钮
  const EditIcon = () => <EditOutlined />;

  // 渲染步骤内容
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <Card>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <Title level={4}>录入职位需求</Title>
                <Paragraph type="secondary">
                  您可以使用语音录入或手动输入职位需求，AI 将自动分析和提取关键信息。
                </Paragraph>
              </div>

              <Tabs
                defaultActiveKey="voice"
                items={[
                  {
                    key: 'voice',
                    label: (
                      <span>
                        <AudioOutlined />
                        语音录入
                      </span>
                    ),
                    children: (
                      <VoiceRecorder
                        onTranscriptionComplete={handleTranscriptionComplete}
                        placeholder="点击录音按钮，描述职位需求..."
                      />
                    ),
                  },
                  {
                    key: 'manual',
                    label: (
                      <span>
                        <EditOutlined />
                        手动输入
                      </span>
                    ),
                    children: (
                      <TextArea
                        placeholder="请输入职位需求描述，例如：招聘一名高级 Python 后端工程师，要求有5年以上工作经验，熟悉 Django、PostgreSQL，月薪 3-5 万，工作地点北京..."
                        value={manualText}
                        onChange={(e) => setManualText(e.target.value)}
                        rows={8}
                        showCount
                        maxLength={5000}
                      />
                    ),
                  },
                ]}
              />

              {(voiceText || manualText) && (
                <Card
                  title="预览"
                  extra={<Tag color="blue">{manualText.length} 字符</Tag>}
                  style={{ background: '#fafafa' }}
                >
                  <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                    {manualText || voiceText}
                  </Paragraph>
                </Card>
              )}
            </Space>
          </Card>
        );

      case 1:
        return (
          <Card loading={isProcessingNlu}>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <Title level={4}>确认 AI 理解</Title>
                <Paragraph type="secondary">
                  请检查 AI 提取的信息是否正确。置信度较低的字段会高亮显示，您可以编辑或确认。
                </Paragraph>
              </div>

              {nluResult && (
                <NluConfirmCard
                  fields={nluResult.fields}
                  originalText={manualText}
                  followUps={nluResult.followUps}
                  onFieldUpdate={handleFieldUpdate}
                  onFollowUpAnswer={handleFollowUpAnswer}
                  onConfirm={handleNluConfirm}
                />
              )}

              {isProcessingNlu && (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Spin size="large" tip="AI 正在分析您的需求..." />
                </div>
              )}
            </Space>
          </Card>
        );

      case 2:
        return (
          <Card>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <Title level={4}>完善职位信息</Title>
                <Paragraph type="secondary">
                  请确认或修改以下信息，确保职位描述准确完整。
                </Paragraph>
              </div>

              <Form layout="vertical">
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="职位名称" required>
                      <Input
                        value={formData.title}
                        onChange={(e) =>
                          setFormData((prev) => ({ ...prev, title: e.target.value }))
                        }
                        placeholder="例如：高级后端工程师"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="工作地点" required>
                      <Select
                        value={formData.location}
                        onChange={(value) =>
                          setFormData((prev) => ({ ...prev, location: value }))
                        }
                        placeholder="选择工作地点"
                      >
                        {cityOptions.map((city) => (
                          <Option key={city} value={city}>
                            {city}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="最低薪资 (元/月)">
                      <Input
                        type="number"
                        value={formData.salaryMin}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            salaryMin: parseInt(e.target.value) || 0,
                          }))
                        }
                        placeholder="例如：30000"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="最高薪资 (元/月)">
                      <Input
                        type="number"
                        value={formData.salaryMax}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            salaryMax: parseInt(e.target.value) || 0,
                          }))
                        }
                        placeholder="例如：50000"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item label="工作类型" required>
                      <Select
                        value={formData.jobType}
                        onChange={(value) =>
                          setFormData((prev) => ({ ...prev, jobType: value }))
                        }
                      >
                        <Option value="full-time">全职</Option>
                        <Option value="part-time">兼职</Option>
                        <Option value="contract">合同制</Option>
                        <Option value="internship">实习</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="经验要求" required>
                      <Select
                        value={formData.experienceLevel}
                        onChange={(value) =>
                          setFormData((prev) => ({ ...prev, experienceLevel: value }))
                        }
                      >
                        <Option value="entry">1年以下</Option>
                        <Option value="junior">1-3年</Option>
                        <Option value="mid">3-5年</Option>
                        <Option value="senior">5-10年</Option>
                        <Option value="expert">10年以上</Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item label="技能要求">
                  <Select
                    mode="multiple"
                    value={formData.skills}
                    onChange={(value) =>
                      setFormData((prev) => ({ ...prev, skills: value }))
                    }
                    placeholder="选择或搜索技能"
                    tokenSeparators={[',']}
                  >
                    {skillOptions.map((skill) => (
                      <Option key={skill} value={skill}>
                        {skill}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item label="职位描述" required>
                  <TextArea
                    value={formData.description}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, description: e.target.value }))
                    }
                    rows={6}
                    placeholder="详细描述职位职责和要求..."
                    showCount
                    maxLength={2000}
                  />
                </Form.Item>
              </Form>
            </Space>
          </Card>
        );

      case 3:
        return (
          <Card>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <div>
                <Title level={4}>确认发布</Title>
                <Paragraph type="secondary">
                  请确认以下职位信息，确认无误后点击发布。
                </Paragraph>
              </div>

              <Card style={{ background: '#fafafa' }}>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="职位名称">
                    <Text strong>{formData.title}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="工作地点">
                    {formData.location}
                  </Descriptions.Item>
                  <Descriptions.Item label="薪资范围">
                    {formData.salaryMin / 10000}万 - {formData.salaryMax / 10000}万/月
                  </Descriptions.Item>
                  <Descriptions.Item label="工作类型">
                    {formData.jobType === 'full-time'
                      ? '全职'
                      : formData.jobType === 'part-time'
                      ? '兼职'
                      : formData.jobType}
                  </Descriptions.Item>
                  <Descriptions.Item label="经验要求">
                    {formData.experienceLevel === 'entry'
                      ? '1年以下'
                      : formData.experienceLevel === 'junior'
                      ? '1-3年'
                      : formData.experienceLevel === 'mid'
                      ? '3-5年'
                      : formData.experienceLevel === 'senior'
                      ? '5-10年'
                      : '10年以上'}
                  </Descriptions.Item>
                  <Descriptions.Item label="技能要求" span={2}>
                    <Space wrap>
                      {formData.skills.map((skill) => (
                        <Tag key={skill} color="blue">
                          {skill}
                        </Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="职位描述" span={2}>
                    <Paragraph style={{ marginBottom: 0 }}>
                      {formData.description}
                    </Paragraph>
                  </Descriptions.Item>
                </Descriptions>
              </Card>

              <Alert
                message="提示"
                description="发布后，AI 将自动为您匹配合适的候选人。您可以在候选人页面查看匹配结果。"
                type="info"
                showIcon
              />
            </Space>
          </Card>
        );

      default:
        return null;
    }
  };

  // 发布成功
  if (isSubmitted) {
    return (
      <Card>
        <Result
          status="success"
          title="职位发布成功！"
          subTitle="您的职位已成功发布，AI 将自动为您匹配合适的候选人。"
          extra={[
            <Button
              type="primary"
              key="view"
              onClick={() => navigate('/employer/jobs')}
            >
              查看职位
            </Button>,
            <Button key="again" onClick={() => window.location.reload()}>
              发布新职位
            </Button>,
          ]}
        />
      </Card>
    );
  }

  return (
    <div className="new-job-page" style={{ padding: 24 }}>
      {/* 步骤条 */}
      <Card style={{ marginBottom: 24 }}>
        <Steps
          current={currentStep}
          status={stepStatuses[currentStep]}
          items={steps.map((step, index) => ({
            title: step.title,
            icon: index < currentStep ? <CheckCircleOutlined /> : step.icon,
          }))}
        />
      </Card>

      {/* 步骤内容 */}
      <div style={{ marginBottom: 24 }}>{renderStepContent()}</div>

      {/* 底部操作 */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={goToPrevStep}
            disabled={currentStep === 0}
          >
            上一步
          </Button>

          <Space>
            <Button onClick={() => navigate('/employer/jobs')}>取消</Button>

            {currentStep < 3 ? (
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={goToNextStep}
                disabled={currentStep === 0 && !manualText}
              >
                {currentStep === 0 ? 'AI 分析' : '下一步'}
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={handleSubmit}
                loading={isSubmitting}
              >
                发布职位
              </Button>
            )}
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default NewJobPage;
