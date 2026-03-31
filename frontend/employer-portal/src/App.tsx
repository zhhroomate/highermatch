import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import JobsPage from "./pages/Jobs";
import CandidatesPage from "./pages/Candidates";
import PipelinePage from "./pages/Pipeline";
import AnalyticsPage from "./pages/Analytics";
import BillingPage from "./pages/Billing";
import LandingPage from "./pages/LandingPage";
import "./index.css";

const NAV_ITEMS = [
  { path:"/dashboard", label:"数据概览", section:"main", icon:(a:boolean) => <svg viewBox="0 0 24 24" fill={a?"#29ABE2":"none"} stroke={a?"#29ABE2":"#64748B"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg> },
  { path:"/jobs", label:"职位管理", section:"main", icon:(a:boolean) => <svg viewBox="0 0 24 24" fill={a?"#29ABE2":"none"} stroke={a?"#29ABE2":"#64748B"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg> },
  { path:"/candidates", label:"候选人库", section:"main", icon:(a:boolean) => <svg viewBox="0 0 24 24" fill={a?"#29ABE2":"none"} stroke={a?"#29ABE2":"#64748B"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg> },
  { path:"/pipeline", label:"招聘管道", section:"main", icon:(a:boolean) => <svg viewBox="0 0 24 24" fill={a?"#29ABE2":"none"} stroke={a?"#29ABE2":"#64748B"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> },
  { path:"/analytics", label:"人才洞察", section:"analytics", icon:(a:boolean) => <svg viewBox="0 0 24 24" fill={a?"#29ABE2":"none"} stroke={a?"#29ABE2":"#64748B"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg> },
  { path:"/billing", label:"账单管理", section:"analytics", icon:(a:boolean) => <svg viewBox="0 0 24 24" fill={a?"#29ABE2":"none"} stroke={a?"#29ABE2":"#64748B"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg> },
];

const Sidebar: React.FC<{ open: boolean; onClose: () => void }> = ({ open, onClose }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  return (
    <>
      {open && <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.3)", zIndex:49 }} onClick={onClose} className="md:hidden" />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-logo">
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <div style={{ width:36, height:36, borderRadius:10, background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
            </div>
            <div>
              <p style={{ fontSize:15, fontWeight:800, color:"#1E293B", lineHeight:1.2 }}>HigherMatch</p>
              <p style={{ fontSize:11, color:"#94A3B8", fontWeight:500 }}>企业招聘平台</p>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <p className="nav-section-label">核心功能</p>
          {NAV_ITEMS.filter(n => n.section === "main").map(item => (
            <div key={item.path} className={`nav-item ${path === item.path || (path === "/" && item.path === "/dashboard") ? "active" : ""}`}
              onClick={() => { navigate(item.path); onClose(); }}>
              {item.icon(path === item.path)}
              {item.label}
            </div>
          ))}
          <p className="nav-section-label" style={{ marginTop:8 }}>数据分析</p>
          {NAV_ITEMS.filter(n => n.section === "analytics").map(item => (
            <div key={item.path} className={`nav-item ${path === item.path ? "active" : ""}`}
              onClick={() => { navigate(item.path); onClose(); }}>
              {item.icon(path === item.path)}
              {item.label}
            </div>
          ))}
        </nav>

        <div style={{ padding:"12px 16px", borderTop:"1px solid #F1F5F9" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 12px", borderRadius:10, background:"#F8FAFC", cursor:"pointer" }}>
            <div style={{ width:32, height:32, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, fontWeight:800, color:"white", flexShrink:0 }}>字</div>
            <div style={{ flex:1, minWidth:0 }}>
              <p style={{ fontSize:13, fontWeight:700, color:"#1E293B", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>字节跳动 HR</p>
              <p style={{ fontSize:11, color:"#94A3B8" }}>企业管理员</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const isLanding = location.pathname === "/";

  if (isLanding) return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
    </Routes>
  );

  return (
    <div className="app-layout">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main-content">
        <header className="top-bar">
          <button onClick={() => setSidebarOpen(true)} style={{ display:"none", background:"none", border:"none", cursor:"pointer", padding:4 }} className="mobile-menu-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width:20, height:20 }}><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
          <div style={{ flex:1 }} />
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <button className="btn-ghost" style={{ position:"relative" }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
              <span style={{ position:"absolute", top:6, right:6, width:8, height:8, borderRadius:"50%", background:"#EF4444", border:"2px solid white" }} />
            </button>
            <div style={{ width:34, height:34, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, fontWeight:800, color:"white", cursor:"pointer" }}>字</div>
          </div>
        </header>
        <main className="page-body">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/candidates" element={<CandidatesPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/billing" element={<BillingPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

const App: React.FC = () => (
  <BrowserRouter>
    <AppLayout />
  </BrowserRouter>
);

export default App;
