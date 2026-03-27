/**
 * HigherMatch™ Employer Portal - 路由配置
 * ==========================================
 *
 * React Router 6 路由配置
 * ⚠️ 开发模式：已移除登录鉴权，所有页面可直接访问
 *
 * 版本: 1.0.0
 */

import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, Link } from 'react-router-dom';
import { Spin } from 'antd';

// ==================== 页面组件 ====================

// 懒加载页面组件
const Dashboard = lazy(() => import('./Dashboard'));
const Login = lazy(() => import('./Login'));
const Jobs = lazy(() => import('../pages/Jobs'));
const Candidates = lazy(() => import('../pages/Candidates'));
const Settings = lazy(() => import('../pages/Settings'));
const NewJobPage = lazy(() => import('../pages/NewJobPage'));
const PipelineBoard = lazy(() => import('../pages/PipelineBoard'));
const BillingPage = lazy(() => import('../pages/BillingPage'));
const OnboardingPage = lazy(() => import('../pages/OnboardingPage'));
const InterviewsPage = lazy(() => import('../pages/InterviewsPage'));
const AnalyticsPage = lazy(() => import('../pages/AnalyticsPage'));

// ==================== 样式 ====================

const layoutStyle: React.CSSProperties = {
  minHeight: '100vh',
};

// ==================== 加载组件 ====================

const PageLoader: React.FC = () => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      background: '#f0f2f5',
    }}
  >
    <Spin size="large" tip="加载中..." />
  </div>
);

// ==================== 雇主端布局 ====================

const EmployerLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [collapsed, setCollapsed] = React.useState(false);

  const menuItems = [
    { key: '/employer/dashboard', icon: '📊', label: '工作台' },
    { key: '/employer/jobs/new', icon: '➕', label: '发布职位' },
    { key: '/employer/jobs', icon: '💼', label: '职位管理' },
    { key: '/employer/jobs/:jobId/pipeline', icon: '📋', label: '候选人管道' },
    { key: '/employer/candidates', icon: '👥', label: '候选人' },
    { key: '/employer/billing', icon: '💳', label: '账单中心' },
    { key: '/employer/onboarding', icon: '✅', label: '入职保障' },
    { key: '/employer/interviews', icon: '📅', label: '面试安排' },
    { key: '/employer/analytics', icon: '📈', label: '数据统计' },
    { key: '/employer/settings', icon: '⚙️', label: '设置' },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* 侧边栏 */}
      <aside
        style={{
          width: collapsed ? 80 : 200,
          background: '#001529',
          transition: 'width 0.2s',
          position: 'fixed',
          height: '100vh',
          overflow: 'auto',
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: collapsed ? 16 : 18,
            fontWeight: 'bold',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          {collapsed ? 'HM' : 'HigherMatch™'}
        </div>

        <div style={{ color: 'rgba(255,255,255,0.65)', padding: '16px 24px', fontSize: 12 }}>
          {collapsed ? '' : '雇主端'}
        </div>

        {menuItems.map((item) => (
          <Link
            key={item.key}
            to={item.key}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '12px 24px',
              color: 'rgba(255,255,255,0.85)',
              textDecoration: 'none',
              transition: 'background 0.3s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.08)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <span style={{ marginRight: 12, fontSize: 16 }}>{item.icon}</span>
            {!collapsed && item.label}
          </Link>
        ))}

        {/* 折叠按钮 */}
        <div
          style={{
            position: 'absolute',
            bottom: 48,
            width: '100%',
            padding: '12px 24px',
            cursor: 'pointer',
            color: 'rgba(255,255,255,0.65)',
          }}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? '→' : '←'}
        </div>
      </aside>

      {/* 主内容区 */}
      <main style={{ flex: 1, marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        {/* 顶部导航 */}
        <header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            height: 64,
            boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
            position: 'sticky',
            top: 0,
            zIndex: 100,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span>👤</span>
            <span style={{ fontSize: 14 }}>开发模式用户</span>
            <span style={{ fontSize: 10, color: '#f5222d', background: '#fff1f0', padding: '2px 8px', borderRadius: 4 }}>
              DEV
            </span>
          </div>
        </header>

        {/* 页面内容 */}
        <div style={{ padding: 24, minHeight: 'calc(100vh - 64px)' }}>{children}</div>

        {/* 页脚 */}
        <footer style={{ textAlign: 'center', padding: '16px 24px', color: '#999', fontSize: 12 }}>
          HigherMatch™ © 2024 - AI 智能招聘平台 | 开发模式运行中
        </footer>
      </main>
    </div>
  );
};

// ==================== 路由配置 ====================

/**
 * ⚠️ 开发模式路由配置
 * 已移除所有 PrivateRoute 守卫，所有页面均可直接访问
 */
const AppRoutes: React.FC = () => {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* 登录页 */}
          <Route path="/employer/login" element={<Login />} />

          {/* 主布局下的路由 - 无鉴权 */}
          <Route
            path="/employer"
            element={
              <EmployerLayout>
                <Outlet />
              </EmployerLayout>
            }
          >
            <Route index element={<Navigate to="/employer/dashboard" replace />} />

            {/* 工作台 */}
            <Route path="dashboard" element={<Dashboard />} />

            {/* 职位管理 */}
            <Route path="jobs" element={<Jobs />} />
            <Route path="jobs/new" element={<NewJobPage />} />
            <Route path="jobs/:jobId/pipeline" element={<PipelineBoard />} />

            {/* 候选人 */}
            <Route path="candidates" element={<Candidates />} />

            {/* 账单与保障 */}
            <Route path="billing" element={<BillingPage />} />
            <Route path="onboarding" element={<OnboardingPage />} />

            {/* 面试与数据 */}
            <Route path="interviews" element={<InterviewsPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />

            {/* 设置 */}
            <Route path="settings" element={<Settings />} />
          </Route>

          {/* 404 重定向 */}
          <Route path="*" element={<Navigate to="/employer/dashboard" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
};

export { EmployerLayout };
export default AppRoutes;
