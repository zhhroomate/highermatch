/**
 * HigherMatch™ Employer Portal - 设置页面
 * ==========================================
 *
 * 版本: 1.0.0
 */

import React from 'react';
import { Typography, Form, Button, Switch, Divider, message, Card, Input } from 'antd';
import { SaveOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const { TextArea } = Input;

/**
 * 设置页面
 */
const Settings: React.FC = () => {
  const onFinish = () => {
    message.success('设置已保存');
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ marginBottom: 24 }}>企业设置</Title>

      <Form layout="vertical" onFinish={onFinish}>
        {/* 基本信息 */}
        <Card title="基本信息" style={{ marginBottom: 16 }} bordered={false}>
          <Form.Item label="公司名称" name="companyName" initialValue="HigherMatch Tech">
            <Input />
          </Form.Item>
          <Form.Item label="所属行业" name="industry" initialValue="互联网">
            <Input />
          </Form.Item>
          <Form.Item label="公司规模" name="size" initialValue="201-500人">
            <Input />
          </Form.Item>
          <Form.Item label="公司简介" name="description" initialValue="">
            <TextArea rows={4} placeholder="请输入公司简介..." />
          </Form.Item>
        </Card>

        {/* 联系方式 */}
        <Card title="联系方式" style={{ marginBottom: 16 }} bordered={false}>
          <Form.Item label="联系人" name="contactName" initialValue="张三">
            <Input />
          </Form.Item>
          <Form.Item label="联系电话" name="contactPhone" initialValue="13800138000">
            <Input />
          </Form.Item>
          <Form.Item label="联系邮箱" name="contactEmail" initialValue="hr@highermatch.com">
            <Input />
          </Form.Item>
        </Card>

        {/* 通知设置 */}
        <Card title="通知设置" style={{ marginBottom: 16 }} bordered={false}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <Text strong>新候选人匹配通知</Text>
              <br />
              <Text type="secondary">当有新的候选人匹配到您的职位时，发送通知</Text>
            </div>
            <Switch defaultChecked />
          </div>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <Text strong>面试提醒</Text>
              <br />
              <Text type="secondary">在面试开始前发送提醒</Text>
            </div>
            <Switch defaultChecked />
          </div>
          <Divider />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Text strong>每周数据报告</Text>
              <br />
              <Text type="secondary">每周一发送招聘数据报告</Text>
            </div>
            <Switch />
          </div>
        </Card>

        <Button type="primary" icon={<SaveOutlined />} htmlType="submit">
          保存设置
        </Button>
      </Form>
    </div>
  );
};

export default Settings;
