import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd-mobile';
import zhCN from 'antd-mobile/es/locales/zh-CN';
import ProfilePage from './routes/ProfilePage';
import Recommendations from './routes/Recommendations';
import Applications from './routes/Applications';
import AIAdvisorBubble from './components/AIAdvisorBubble';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/recommendations" replace />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/applications" element={<Applications />} />
        </Routes>
        <AIAdvisorBubble />
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
