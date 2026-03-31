import React, { useState } from "react";
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from "react-router-dom";
import VoiceResume from "./routes/VoiceResume";
import Recommendations from "./routes/Recommendations";
import Applications from "./routes/Applications";
import KnowledgeGraph from "./routes/KnowledgeGraph";
import ProfilePage from "./routes/ProfilePage";
import AIAdvisorBubble from "./components/AIAdvisorBubble";
import "./index.css";

const NAV_TABS = [
  {
    path: "/", label: "推荐",
    icon: (active: boolean) => (
      <svg viewBox="0 0 24 24" fill={active ? "#29ABE2" : "none"} stroke={active ? "#29ABE2" : "#94A3B8"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-tab-icon">
        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9,22 9,12 15,12 15,22"/>
      </svg>
    )
  },
  {
    path: "/applications", label: "申请",
    icon: (active: boolean) => (
      <svg viewBox="0 0 24 24" fill={active ? "#29ABE2" : "none"} stroke={active ? "#29ABE2" : "#94A3B8"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-tab-icon">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10,9 9,9 8,9"/>
      </svg>
    )
  },
  {
    path: "/voice-resume", label: "语音简历",
    icon: (active: boolean) => (
      <svg viewBox="0 0 24 24" fill={active ? "#29ABE2" : "none"} stroke={active ? "#29ABE2" : "#94A3B8"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-tab-icon">
        <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    )
  },
  {
    path: "/knowledge-graph", label: "图谱",
    icon: (active: boolean) => (
      <svg viewBox="0 0 24 24" fill={active ? "#29ABE2" : "none"} stroke={active ? "#29ABE2" : "#94A3B8"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-tab-icon">
        <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
      </svg>
    )
  },
  {
    path: "/profile", label: "我的",
    icon: (active: boolean) => (
      <svg viewBox="0 0 24 24" fill={active ? "#29ABE2" : "none"} stroke={active ? "#29ABE2" : "#94A3B8"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-tab-icon">
        <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>
      </svg>
    )
  },
];

const BottomNav: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const path = location.pathname;

  return (
    <nav className="bottom-nav">
      {NAV_TABS.map(tab => {
        const active = path === tab.path || (path === "/" && tab.path === "/");
        return (
          <button key={tab.path} className={`nav-tab ${active ? "active" : ""}`} onClick={() => navigate(tab.path)}>
            {tab.icon(active)}
            <span className="nav-tab-label" style={{ color: active ? "#29ABE2" : undefined }}>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
};

const AppLayout: React.FC = () => (
  <div style={{ position: "relative" }}>
    <Routes>
      <Route path="/" element={<Recommendations />} />
      <Route path="/applications" element={<Applications />} />
      <Route path="/voice-resume" element={<VoiceResume />} />
      <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="*" element={<Recommendations />} />
    </Routes>
    <BottomNav />
    <AIAdvisorBubble />
  </div>
);

const App: React.FC = () => (
  <BrowserRouter>
    <AppLayout />
  </BrowserRouter>
);

export default App;
