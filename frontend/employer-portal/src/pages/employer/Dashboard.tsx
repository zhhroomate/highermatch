import React from "react";
import { useLocation } from "wouter";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const DATA = [
  { name: "1月", 申请: 45, 面试: 18, 入职: 3 }, { name: "2月", 申请: 62, 面试: 24, 入职: 5 },
  { name: "3月", 申请: 78, 面试: 31, 入职: 7 }, { name: "4月", 申请: 91, 面试: 38, 入职: 9 },
  { name: "5月", 申请: 85, 面试: 35, 入职: 8 }, { name: "6月", 申请: 110, 面试: 46, 入职: 12 },
];

const CANDIDATES = [
  { name: "李晓明", role: "高级后端工程师", score: 96, status: "面试中" },
  { name: "王芳", role: "推荐算法工程师", score: 91, status: "审核中" },
  { name: "张伟", role: "前端架构师", score: 88, status: "已发Offer" },
];

export default function Dashboard() {
  const [, navigate] = useLocation();

  return (
    <div className="hm-fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: "clamp(22px,3vw,32px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>数据概览</h1>
          <p style={{ fontSize: 14, color: "#A3A3A3" }}>实时掌握招聘进展</p>
        </div>
        <button className="hm-btn hm-btn-primary" onClick={() => navigate("/employer/jobs")}>+ 发布新职位</button>
      </div>

      {/* 统计 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12, marginBottom: 28 }}>
        {[
          { label: "活跃职位", value: "12", sub: "+3 本月" },
          { label: "本月申请", value: "247", sub: "+18%" },
          { label: "面试中", value: "38", sub: "+5" },
          { label: "成功入职", value: "9", sub: "+2" },
        ].map((s, i) => (
          <div key={i} className="hm-card-flat" style={{ padding: 20 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: "#A3A3A3", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</p>
            <p style={{ fontSize: 28, fontWeight: 900, color: "#0A0A0A", letterSpacing: "-0.03em" }}>{s.value}</p>
            <p style={{ fontSize: 12, color: "#737373", marginTop: 4 }}>{s.sub}</p>
          </div>
        ))}
      </div>

      {/* 图表 */}
      <div className="hm-card-flat" style={{ padding: 24, marginBottom: 20 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A", marginBottom: 20 }}>招聘趋势</h3>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={DATA}>
            <defs>
              <linearGradient id="gBlack" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0A0A0A" stopOpacity={0.08}/>
                <stop offset="95%" stopColor="#0A0A0A" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F1F1" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#A3A3A3" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: "#A3A3A3" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "white", border: "1px solid #E5E5E5", borderRadius: 12, fontSize: 13, boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }} />
            <Area type="monotone" dataKey="申请" stroke="#0A0A0A" strokeWidth={2} fill="url(#gBlack)" />
            <Area type="monotone" dataKey="面试" stroke="#A3A3A3" strokeWidth={1.5} fill="none" strokeDasharray="4 4" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 最新候选人 */}
      <div className="hm-card-flat" style={{ overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #F5F5F5" }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A" }}>AI 推荐候选人</h3>
          <button className="hm-btn hm-btn-ghost hm-btn-sm" onClick={() => navigate("/employer/candidates")}>查看全部</button>
        </div>
        <div>
          {CANDIDATES.map((c, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 20px", borderBottom: i < CANDIDATES.length - 1 ? "1px solid #F8F8F8" : "none" }}>
              <div className="hm-avatar hm-avatar-md" style={{ background: "#0A0A0A", color: "white" }}>{c.name[0]}</div>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 14, fontWeight: 600, color: "#0A0A0A" }}>{c.name}</p>
                <p style={{ fontSize: 12, color: "#A3A3A3" }}>{c.role}</p>
              </div>
              <div className="hm-score" style={{ width: 40, height: 40, fontSize: 14 }}>{c.score}</div>
              <span className="hm-tag hm-tag-light">{c.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
