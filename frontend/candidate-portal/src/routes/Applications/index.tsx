import React, { useState, useEffect } from "react";
import { apiClient } from "../../api/client";

interface Application {
  id: string; jobTitle: string; company: string; status: string;
  appliedAt: string; salary: string; nextStep?: string; interviewDate?: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  pending:   { label:"待处理", color:"#D97706", bg:"#FFFBEB", icon:"⏳" },
  reviewing: { label:"简历审核", color:"#29ABE2", bg:"#EBF8FF", icon:"👀" },
  interview: { label:"面试邀请", color:"#7C3AED", bg:"#F5F3FF", icon:"🎯" },
  offer:     { label:"已发Offer", color:"#059669", bg:"#ECFDF5", icon:"🎉" },
  rejected:  { label:"未通过", color:"#94A3B8", bg:"#F8FAFC", icon:"✗" },
};

const MOCK: Application[] = [
  { id:"1", jobTitle:"高级后端工程师", company:"字节跳动", status:"interview", appliedAt:"2天前", salary:"35-50K", nextStep:"技术面试", interviewDate:"明天 14:00" },
  { id:"2", jobTitle:"推荐算法工程师", company:"阿里巴巴", status:"reviewing", appliedAt:"4天前", salary:"40-60K", nextStep:"等待 HR 回复" },
  { id:"3", jobTitle:"后端工程师", company:"腾讯", status:"offer", appliedAt:"2周前", salary:"28-45K", nextStep:"确认入职意向" },
  { id:"4", jobTitle:"数据工程师", company:"美团", status:"pending", appliedAt:"1天前", salary:"30-45K" },
  { id:"5", jobTitle:"iOS 工程师", company:"滴滴", status:"rejected", appliedAt:"3周前", salary:"30-45K" },
];

const Applications: React.FC = () => {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"all"|"active"|"done">("all");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await apiClient.get<{ items: Application[] }>("/applications");
        setApps(res.items || MOCK);
      } catch { setApps(MOCK); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const filtered = apps.filter(a => tab === "active" ? ["pending","reviewing","interview"].includes(a.status) : tab === "done" ? ["offer","rejected"].includes(a.status) : true);
  const stats = { total:apps.length, active:apps.filter(a=>["pending","reviewing","interview"].includes(a.status)).length, offer:apps.filter(a=>a.status==="offer").length, interview:apps.filter(a=>a.status==="interview").length };

  return (
    <div className="page-container">
      <div className="top-nav">
        <h1 style={{ fontSize:18, fontWeight:800, color:"#1E293B" }}>我的申请</h1>
        <span style={{ fontSize:12, color:"#94A3B8", background:"#F8FAFC", padding:"4px 10px", borderRadius:100 }}>{stats.total} 个</span>
      </div>
      <div style={{ padding:"16px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10, marginBottom:20 }}>
          {[{label:"进行中",value:stats.active,color:"#29ABE2",bg:"#EBF8FF"},{label:"面试邀请",value:stats.interview,color:"#7C3AED",bg:"#F5F3FF"},{label:"已获Offer",value:stats.offer,color:"#059669",bg:"#ECFDF5"}].map(s => (
            <div key={s.label} style={{ background:s.bg, borderRadius:14, padding:"14px 10px", textAlign:"center" }}>
              <p style={{ fontSize:22, fontWeight:800, color:s.color, marginBottom:2 }}>{s.value}</p>
              <p style={{ fontSize:11, color:"#64748B", fontWeight:600 }}>{s.label}</p>
            </div>
          ))}
        </div>
        <div style={{ display:"flex", gap:8, marginBottom:16 }}>
          {[{key:"all",label:"全部"},{key:"active",label:"进行中"},{key:"done",label:"已结束"}].map(t => (
            <button key={t.key} onClick={() => setTab(t.key as any)} style={{ padding:"6px 16px", borderRadius:100, fontSize:13, fontWeight:600, cursor:"pointer", border:"none", transition:"all 0.2s", background:tab===t.key?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F8FAFC", color:tab===t.key?"white":"#64748B", boxShadow:tab===t.key?"0 2px 8px rgba(41,171,226,0.3)":"none" }}>{t.label}</button>
          ))}
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {loading ? Array.from({length:3}).map((_,i) => (
            <div key={i} style={{ background:"white", borderRadius:16, padding:16, border:"1px solid #F1F5F9" }}>
              <div className="skeleton" style={{ height:16, borderRadius:8, width:"60%", marginBottom:8 }} />
              <div className="skeleton" style={{ height:12, borderRadius:8, width:"40%" }} />
            </div>
          )) : filtered.map((app,i) => {
            const cfg = STATUS_CONFIG[app.status] || STATUS_CONFIG.pending;
            return (
              <div key={app.id} className="card fade-in" style={{ padding:16, animationDelay:`${i*0.05}s` }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
                  <div style={{ flex:1 }}>
                    <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B", marginBottom:2 }}>{app.jobTitle}</h3>
                    <p style={{ fontSize:13, color:"#64748B" }}>{app.company}</p>
                  </div>
                  <span style={{ fontSize:12, fontWeight:700, color:cfg.color, background:cfg.bg, padding:"4px 10px", borderRadius:100, flexShrink:0 }}>{cfg.icon} {cfg.label}</span>
                </div>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:app.nextStep?10:0 }}>
                  <span style={{ fontSize:13, fontWeight:700, color:"#059669" }}>{app.salary}</span>
                  <span style={{ fontSize:11, color:"#94A3B8" }}>{app.appliedAt}申请</span>
                </div>
                {app.nextStep && (
                  <div style={{ background:app.status==="interview"?"#F5F3FF":"#F8FAFC", borderRadius:10, padding:"8px 12px", display:"flex", alignItems:"center", gap:8 }}>
                    <span style={{ fontSize:14 }}>{app.status==="interview"?"📅":"💬"}</span>
                    <div>
                      <p style={{ fontSize:12, fontWeight:700, color:app.status==="interview"?"#7C3AED":"#64748B" }}>{app.nextStep}</p>
                      {app.interviewDate && <p style={{ fontSize:11, color:"#94A3B8", marginTop:1 }}>{app.interviewDate}</p>}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Applications;
