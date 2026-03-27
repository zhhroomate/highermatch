/**
 * HigherMatch™ Employer Portal - 登录页面
 * ==========================================
 *
 * 版本: 1.0.0
 */

import React, { useState } from 'react';
import { Form, Input, Button, Typography, message, Checkbox, Card } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiClient } from '../../api/client';

const { Title, Text } = Typography;

/**
 * 登录页面
 */
const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // 获取跳转来源
  const from = (location.state as any)?.from?.pathname || '/employer/dashboard';

  const onFinish = async (values: { email: string; password: string; remember: boolean }) => {
    setLoading(true);

    try {
      // 调用登录 API
      const response = await apiClient.post('/auth/login', {
        email: values.email,
        password: values.password,
      });

      const { access_token, refresh_token, user } = response.data;

      // 保存 token
      apiClient.setTokens(access_token, refresh_token);

      // 保存用户信息
      localStorage.setItem('user_info', JSON.stringify(user));

      message.success('登录成功！');

      // 跳转到来源页面或 Dashboard
      navigate(from, { replace: true });
    } catch (error) {
      message.error('登录失败，请检查邮箱和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card
        style={{
          width: 400,
          borderRadius: 16,
          boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
        }}
        styles={{ body: { padding: 40 } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2} style={{ marginBottom: 8 }}>
            HigherMatch™
          </Title>
          <Text type="secondary">雇主端登录</Text>
        </div>

        <Form
          name="login"
          initialValues={{ remember: true }}
          onFinish={onFinish}
          size="large"
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '请输入有效的邮箱地址' },
            ]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="邮箱地址"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密码"
            />
          </Form.Item>

          <Form.Item>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>记住我</Checkbox>
              </Form.Item>
              <a href="/employer/forgot-password" style={{ color: '#1890ff' }}>
                忘记密码？
              </a>
            </div>
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: 44, borderRadius: 8 }}
            >
              登录
            </Button>
          </Form.Item>

          <div style={{ textAlign: 'center' }}>
            <Text type="secondary">还没有账号？</Text>
            <a href="/employer/register" style={{ color: '#1890ff', marginLeft: 8 }}>
              立即注册
            </a>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
