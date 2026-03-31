import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

const AREA_DATA = [
  {name:"1月",申请:45,面试:18,入职:3},{name:"2月",申请:62,面试:24,入职:5},
  {name:"3月",申请:78,面试:31,入职:7},{name:"4月",申请:91,面试:38,入职:9},
  {name:"5月",申请:85,面试:35,入职:8},{name:"6月",申请:110,面试:46,入职:12},
];
const BAR_DATA = [
  {name:"后端",value:38},{name:"前端",value:24},{name:"算法",value:19},
  {name:"产品",value:14},{name:"设计",value:8},{name:"运营",value:6},
];

const RECENT_CANDIDATES = [
  { name:"李晓明", title:"高级后端工程师", score:96, status:"interview", avatar:"李" },
  { name:"王芳", title:"推荐算法工程师", score:91, status:"reviewing", avatar:"王" },
  { name:"张伟", title:"前端工程师", score:88, status:"offer", avatar:"张" },
  { name:"陈静", title:"产品经理", score:84, status:"pending", avatar:"陈" },
];

const STATUS_MAP: Record<string, { label:string; color:string; bg:string }> = {
  pending:   { label:"待处理", color:"#D97706", bg:"#FFFBEB" },
  reviewing: { label:"审核中", color:"#29ABE2", bg:"#EBF8FF" },
  interview: { label:"面试中", color:"#7C3AED", bg:"#F5F3FF" },
  offer:     { label:"已发Offer", color:"#059669", bg:"#ECFDF5" },
};

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const stats = [
    { label:"活跃职位", value:"12", change:"+3", up:true, icon:"💼", color:"#29ABE2", bg:"#EBF8FF" },
    { label:"本月申请", value:"247", change:"+18%", up:true, icon:"📋", color:"#7C3AED", bg:"#F5F3FF" },
    { label:"面试中", value:"38", change:"+5", up:true, icon:"🎯", color:"#059669", bg:"#ECFDF5" },
    { label:"成功入职", value:"9", change:"+2", up:true, icon:"🎉", color:"#D97706", bg:"#FFFBEB" },
  ];

  return (
    <div className="fade-in">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:24 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:4 }}>数据概览</h1>
          <p style={{ fontSize:14, color:"#64748B" }}>实时掌握招聘进展，AI 助力精准决策</p>
        </div>
        <button className="btn-primary" onClick={() => navigate("/jobs")}>
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          发布新职位
        </button>
      </div>

      {/* 统计卡片 */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:16, marginBottom:24 }}>
        {stats.map((s,i) => (
          <div key={i} className="stat-card">
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:12 }}>
              <div style={{ width:40, height:40, borderRadius:10, background:s.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:18 }}>{s.icon}</div>
              <span style={{ fontSize:12, fontWeight:700, color:s.up?"#059669":"#EF4444", background:s.up?"#ECFDF5":"#FFF1F2", padding:"2px 8px", borderRadius:100 }}>{s.change}</span>
            </div>
            <p style={{ fontSize:26, fontWeight:800, color:"#1E293B", marginBottom:4 }}>{s.value}</p>
            <p style={{ fontSize:13, color:"#64748B" }}>{s.label}</p>
          </div>
        ))}
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"2fr 1fr", gap:20, marginBottom:20 }}>
        {/* 趋势图 */}
        <div className="card" style={{ padding:20 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
            <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B" }}>招聘漏斗趋势</h3>
            <div style={{ display:"flex", gap:12, fontSize:12, color:"#64748B" }}>
              {[{c:"#29ABE2",l:"申请"},{c:"#4ECDC4",l:"面试"},{c:"#059669",l:"入职"}].map(i => (
                <div key={i.l} style={{ display:"flex", alignItems:"center", gap:4 }}>
                  <div style={{ width:8, height:8, borderRadius:"50%", background:i.c }} />{i.l}
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={AREA_DATA}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#29ABE2" stopOpacity={0.15}/><stop offset="95%" stopColor="#29ABE2" stopOpacity={0}/></linearGradient>
                <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#4ECDC4" stopOpacity={0.15}/><stop offset="95%" stopColor="#4ECDC4" stopOpacity={0}/></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="name" tick={{ fontSize:12, fill:"#94A3B8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize:12, fill:"#94A3B8" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius:10, border:"1px solid #E2E8F0", boxShadow:"0 4px 12px rgba(0,0,0,0.08)" }} />
              <Area type="monotone" dataKey="申请" stroke="#29ABE2" strokeWidth={2} fill="url(#g1)" />
              <Area type="monotone" dataKey="面试" stroke="#4ECDC4" strokeWidth={2} fill="url(#g2)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* 岗位分布 */}
        <div className="card" style={{ padding:20 }}>
          <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B", marginBottom:20 }}>岗位需求分布</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={BAR_DATA} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize:11, fill:"#94A3B8" }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize:12, fill:"#64748B" }} axisLine={false} tickLine={false} width={32} />
              <Tooltip contentStyle={{ borderRadius:10, border:"1px solid #E2E8F0" }} />
              <Bar dataKey="value" fill="#29ABE2" radius={[0,4,4,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 最新候选人 */}
      <div className="card" style={{ padding:20 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
          <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B" }}>最新 AI 推荐候选人</h3>
          <button className="btn-secondary" onClick={() => navigate("/candidates")} style={{ fontSize:12, padding:"6px 14px" }}>查看全部</button>
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
          {RECENT_CANDIDATES.map((c,i) => {
            const st = STATUS_MAP[c.status];
            return (
              <div key={i} style={{ display:"flex", alignItems:"center", gap:14, padding:"12px 0", borderBottom:i<RECENT_CANDIDATES.length-1?"1px solid #F1F5F9":"none" }}>
                <div style={{ width:40, height:40, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:14, fontWeight:800, color:"white", flexShrink:0 }}>{c.avatar}</div>
                <div style={{ flex:1 }}>
                  <p style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:1 }}>{c.name}</p>
                  <p style={{ fontSize:12, color:"#64748B" }}>{c.title}</p>
                </div>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <div style={{ textAlign:"center" }}>
                    <p style={{ fontSize:16, fontWeight:800, color:c.score>=90?"#059669":c.score>=80?"#29ABE2":"#D97706" }}>{c.score}%</p>
                    <p style={{ fontSize:10, color:"#94A3B8" }}>匹配度</p>
                  </div>
                  <span style={{ fontSize:11, fontWeight:700, color:st.color, background:st.bg, padding:"3px 10px", borderRadius:100 }}>{st.label}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
