import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title, Paragraph } = Typography;

const AnalyticsPage: React.FC = () => {
  return (
    <Card>
      <Title level={3}>数据统计</Title>
      <Paragraph type="secondary">查看招聘数据和 AI 分析报告</Paragraph>
      <div style={{ marginTop: 40 }}>
        <Empty description="数据统计功能开发中..." />
      </div>
    </Card>
  );
};

export default AnalyticsPage;
