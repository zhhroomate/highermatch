/**
 * HigherMatch™ Employer Portal - App 入口
 * ==========================================
 *
 * 版本: 1.0.0
 */

import React from 'react';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppRoutes from './routes';

// ==================== Antd 主题配置 ====================

const theme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    borderRadius: 8,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Button: {
      controlHeight: 40,
      paddingContentHorizontal: 20,
    },
    Input: {
      controlHeight: 40,
    },
    Select: {
      controlHeight: 40,
    },
  },
};

// ==================== App 组件 ====================

function App() {
  return (
    <ConfigProvider theme={theme} locale={zhCN}>
      <AppRoutes />
    </ConfigProvider>
  );
}

export default App;
