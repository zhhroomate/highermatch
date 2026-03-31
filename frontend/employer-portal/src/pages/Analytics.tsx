import React from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";

const RADAR_DATA = [
  {subject:"技术能力",A:88,fullMark:100},{subject:"沟通表达",A:75,fullMark:100},
  {subject:"团队协作",A:82,fullMark:100},{subject:"学习能力",A:90,fullMark:100},
  {subject:"项目经验",A:85,fullMark:100},{subject:"行业知识",A:78,fullMark:100},
];
const PIE_DATA = [
  {name:"技术类",value:45,color:"#29ABE2"},{name:"产品类",value:20,color:"#4ECDC4"},
  {name:"设计类",value:15,color:"#7C3AED"},{name:"运营类",value:12,color:"#D97706"},
  {name:"其他",value:8,color:"#94A3B8"},
];
const SALARY_DATA = [
  {range:"10-20K",count:18},{range:"20-30K",count:35},{range:"30-40K",count:42},
  {range:"40-50K",count:28},{range:"50K+",count:15},
];

const AnalyticsPage: React.FC = () => (
  <div className="fade-in">
    <div style={{ marginBottom:24 }}>
      <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:4 }}>人才洞察报告</h1>
      <p style={{ fontSize:14, color:"#64748B" }}>基于平台数据，深度分析行业人才趋势</p>
    </div>

    {/* 核心指标 */}
    <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:16, marginBottom:24 }}>
      {[
        {label:"人才库规模",value:"12,847",sub:"较上月 +8.3%",color:"#29ABE2",bg:"#EBF8FF"},
        {label:"平均匹配度",value:"87.3%",sub:"行业领先水平",color:"#059669",bg:"#ECFDF5"},
        {label:"平均薪资",value:"¥32.5K",sub:"较上月 +2.1%",color:"#7C3AED",bg:"#F5F3FF"},
        {label:"入职成功率",value:"73.2%",sub:"较上月 +5.4%",color:"#D97706",bg:"#FFFBEB"},
      ].map(s => (
        <div key={s.label} className="stat-card">
          <div style={{ width:36, height:36, borderRadius:10, background:s.bg, display:"flex", alignItems:"center", justifyContent:"center", marginBottom:12 }}>
            <div style={{ width:12, height:12, borderRadius:"50%", background:s.color }} />
          </div>
          <p style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:2 }}>{s.value}</p>
          <p style={{ fontSize:13, color:"#64748B", marginBottom:2 }}>{s.label}</p>
          <p style={{ fontSize:11, color:s.color, fontWeight:600 }}>{s.sub}</p>
        </div>
      ))}
    </div>

    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:20 }}>
      {/* 能力雷达 */}
      <div className="card" style={{ padding:20 }}>
        <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B", marginBottom:16 }}>候选人能力画像</h3>
        <ResponsiveContainer width="100%" height={200}>
          <RadarChart data={RADAR_DATA}>
            <PolarGrid stroke="#F1F5F9" />
            <PolarAngleAxis dataKey="subject" tick={{ fontSize:11, fill:"#64748B" }} />
            <Radar name="平均水平" dataKey="A" stroke="#29ABE2" fill="#29ABE2" fillOpacity={0.15} strokeWidth={2} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* 岗位分布 */}
      <div className="card" style={{ padding:20 }}>
        <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B", marginBottom:16 }}>岗位类型分布</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={PIE_DATA} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
              {PIE_DATA.map((entry,i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip contentStyle={{ borderRadius:10, border:"1px solid #E2E8F0" }} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ display:"flex", flexWrap:"wrap", gap:8, justifyContent:"center" }}>
          {PIE_DATA.map(d => <div key={d.name} style={{ display:"flex", alignItems:"center", gap:4, fontSize:11, color:"#64748B" }}><div style={{ width:8, height:8, borderRadius:"50%", background:d.color }} />{d.name}</div>)}
        </div>
      </div>

      {/* 薪资分布 */}
      <div className="card" style={{ padding:20 }}>
        <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B", marginBottom:16 }}>薪资区间分布</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={SALARY_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
            <XAxis dataKey="range" tick={{ fontSize:10, fill:"#94A3B8" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize:11, fill:"#94A3B8" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ borderRadius:10, border:"1px solid #E2E8F0" }} />
            <Bar dataKey="count" fill="#4ECDC4" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
);

export default AnalyticsPage;
