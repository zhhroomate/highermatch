import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title, Paragraph } = Typography;

const InterviewsPage: React.FC = () => {
  return (
    <Card>
      <Title level={3}>面试安排</Title>
      <Paragraph type="secondary">管理和安排候选人面试</Paragraph>
      <div style={{ marginTop: 40 }}>
        <Empty description="面试安排功能开发中..." />
      </div>
    </Card>
  );
};

export default InterviewsPage;
