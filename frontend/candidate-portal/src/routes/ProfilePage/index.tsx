import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"profile"|"services"|"settings">("profile");
  const profile = { name:"张明", title:"高级后端工程师", location:"北京", completeness:85, skills:["Python","Go","PostgreSQL","Redis","Kafka","微服务","推荐系统"] };
  const services = [
    { icon:"✨", title:"简历深度优化", desc:"AI 分析简历，提升通过率 3 倍", price:"¥99", tag:"热门" },
    { icon:"🎯", title:"面试模拟训练", desc:"真实面试场景，AI 实时反馈", price:"¥199", tag:"推荐" },
    { icon:"🗺️", title:"职业规划咨询", desc:"专业顾问 1v1，制定成长路径", price:"¥299", tag:"" },
    { icon:"🔍", title:"背景调查核验", desc:"学历/经历多源核验，增加可信度", price:"¥49", tag:"" },
  ];

  return (
    <div className="page-container">
      <div style={{ background:"linear-gradient(160deg,#EBF8FF 0%,#F0F7FF 60%,#E8F5F3 100%)", padding:"20px 16px 0" }}>
        <div style={{ display:"flex", alignItems:"center", gap:14, marginBottom:16 }}>
          <div style={{ width:64, height:64, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:24, fontWeight:800, color:"white", boxShadow:"0 4px 16px rgba(41,171,226,0.35)", flexShrink:0 }}>{profile.name[0]}</div>
          <div style={{ flex:1 }}>
            <h2 style={{ fontSize:18, fontWeight:800, color:"#1E293B", marginBottom:2 }}>{profile.name}</h2>
            <p style={{ fontSize:13, color:"#64748B", marginBottom:6 }}>{profile.title} · {profile.location}</p>
            <div style={{ display:"flex", alignItems:"center", gap:6 }}>
              <div style={{ flex:1, height:5, borderRadius:3, background:"#E2E8F0", overflow:"hidden" }}>
                <div style={{ height:"100%", width:`${profile.completeness}%`, borderRadius:3, background:"linear-gradient(90deg,#29ABE2,#4ECDC4)" }} />
              </div>
              <span style={{ fontSize:11, fontWeight:700, color:"#29ABE2", flexShrink:0 }}>简历完整度 {profile.completeness}%</span>
            </div>
          </div>
        </div>
        <div style={{ display:"flex", gap:0, borderBottom:"1px solid #E2E8F0" }}>
          {[{key:"profile",label:"我的档案"},{key:"services",label:"增值服务"},{key:"settings",label:"设置"}].map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key as any)} style={{ flex:1, padding:"10px 0", fontSize:13, fontWeight:activeTab===t.key?700:500, color:activeTab===t.key?"#29ABE2":"#94A3B8", background:"none", border:"none", cursor:"pointer", borderBottom:activeTab===t.key?"2.5px solid #29ABE2":"2.5px solid transparent" }}>{t.label}</button>
          ))}
        </div>
      </div>

      <div style={{ padding:"16px" }}>
        {activeTab === "profile" && (
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
            <div className="card" style={{ padding:16 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
                <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>核心技能</h3>
                <span style={{ fontSize:12, color:"#29ABE2", fontWeight:600 }}>编辑</span>
              </div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                {profile.skills.map(s => <span key={s} className="tag tag-blue">{s}</span>)}
                <span className="tag" style={{ background:"#F8FAFC", color:"#94A3B8", border:"1.5px dashed #E2E8F0", cursor:"pointer" }}>+ 添加</span>
              </div>
            </div>
            <div className="card" style={{ padding:16 }}>
              <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:12 }}>教育背景</h3>
              <div style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{ width:40, height:40, borderRadius:10, background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:18 }}>🎓</div>
                <div>
                  <p style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>北京大学</p>
                  <p style={{ fontSize:12, color:"#64748B" }}>计算机科学与技术 · 本科 · 2019</p>
                </div>
              </div>
            </div>
            <button className="btn-brand" onClick={() => navigate("/voice-resume")}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
              语音更新简历
            </button>
          </div>
        )}
        {activeTab === "services" && (
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            <div style={{ background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", borderRadius:16, padding:"14px 16px", marginBottom:4 }}>
              <p style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:4 }}>🚀 提升求职成功率</p>
              <p style={{ fontSize:12, color:"#64748B", lineHeight:1.6 }}>使用增值服务的求职者平均面试邀请率提升 2.8 倍，入职周期缩短 40%</p>
            </div>
            {services.map((s,i) => (
              <div key={i} className="card" style={{ padding:16, display:"flex", alignItems:"center", gap:14 }}>
                <div style={{ width:48, height:48, borderRadius:14, background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:22, flexShrink:0 }}>{s.icon}</div>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:2 }}>
                    <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>{s.title}</h3>
                    {s.tag && <span style={{ fontSize:10, fontWeight:700, color:"#29ABE2", background:"#EBF8FF", padding:"1px 6px", borderRadius:100 }}>{s.tag}</span>}
                  </div>
                  <p style={{ fontSize:12, color:"#64748B", lineHeight:1.5 }}>{s.desc}</p>
                </div>
                <div style={{ textAlign:"right", flexShrink:0 }}>
                  <p style={{ fontSize:15, fontWeight:800, color:"#29ABE2", marginBottom:4 }}>{s.price}</p>
                  <button style={{ padding:"5px 12px", borderRadius:8, background:"linear-gradient(135deg,#29ABE2,#1A8FBF)", color:"white", fontSize:11, fontWeight:700, border:"none", cursor:"pointer" }}>购买</button>
                </div>
              </div>
            ))}
          </div>
        )}
        {activeTab === "settings" && (
          <div style={{ display:"flex", flexDirection:"column", gap:2 }}>
            {[{icon:"🔔",label:"消息通知",desc:"面试邀请、申请状态更新"},{icon:"🔒",label:"隐私设置",desc:"控制简历可见范围"},{icon:"📊",label:"求职偏好",desc:"期望薪资、工作地点、行业"},{icon:"🌐",label:"语言设置",desc:"中文（简体）"},{icon:"❓",label:"帮助中心",desc:"常见问题与使用指南"}].map((item,i) => (
              <div key={i} style={{ display:"flex", alignItems:"center", gap:14, padding:"14px 0", borderBottom:"1px solid #F1F5F9", cursor:"pointer" }}>
                <div style={{ width:38, height:38, borderRadius:10, background:"#F8FAFC", display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, flexShrink:0 }}>{item.icon}</div>
                <div style={{ flex:1 }}>
                  <p style={{ fontSize:14, fontWeight:600, color:"#1E293B" }}>{item.label}</p>
                  <p style={{ fontSize:12, color:"#94A3B8" }}>{item.desc}</p>
                </div>
                <svg viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><polyline points="9,18 15,12 9,6"/></svg>
              </div>
            ))}
            <button style={{ marginTop:20, padding:"12px", borderRadius:12, background:"#FFF1F2", color:"#E11D48", fontWeight:700, fontSize:14, border:"1px solid #FECDD3", cursor:"pointer", width:"100%" }}>退出登录</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
