import React, { useState } from "react";

interface Candidate { id:string; name:string; title:string; location:string; experience:string; score:number; skills:string[]; status:string; verified:boolean; salary:string; }

const MOCK: Candidate[] = [
  { id:"1", name:"李晓明", title:"高级后端工程师", location:"北京", experience:"5年", score:96, skills:["Python","Go","微服务"], status:"interview", verified:true, salary:"35-50K" },
  { id:"2", name:"王芳", title:"推荐算法工程师", location:"杭州", experience:"4年", score:91, skills:["机器学习","Python","Spark"], status:"reviewing", verified:true, salary:"40-60K" },
  { id:"3", name:"张伟", title:"前端工程师", location:"深圳", experience:"3年", score:88, skills:["React","TypeScript","Vue"], status:"offer", verified:false, salary:"25-40K" },
  { id:"4", name:"陈静", title:"产品经理", location:"北京", experience:"4年", score:84, skills:["B端产品","数据分析","Figma"], status:"pending", verified:true, salary:"20-35K" },
  { id:"5", name:"刘洋", title:"数据分析师", location:"上海", experience:"3年", score:79, skills:["SQL","Python","Tableau"], status:"pending", verified:false, salary:"18-28K" },
];

const STATUS_MAP: Record<string, { label:string; color:string; bg:string }> = {
  pending:   { label:"待处理", color:"#D97706", bg:"#FFFBEB" },
  reviewing: { label:"审核中", color:"#29ABE2", bg:"#EBF8FF" },
  interview: { label:"面试中", color:"#7C3AED", bg:"#F5F3FF" },
  offer:     { label:"已发Offer", color:"#059669", bg:"#ECFDF5" },
};

const CandidatesPage: React.FC = () => {
  const [candidates] = useState<Candidate[]>(MOCK);
  const [selected, setSelected] = useState<Candidate|null>(null);
  const [filter, setFilter] = useState("all");

  const filtered = candidates.filter(c => filter === "all" || c.status === filter);

  return (
    <div className="fade-in" style={{ display:"grid", gridTemplateColumns:selected?"1fr 360px":"1fr", gap:20 }}>
      <div>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:24 }}>
          <div>
            <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:4 }}>候选人库</h1>
            <p style={{ fontSize:14, color:"#64748B" }}>AI 精准推荐，多源数据核验</p>
          </div>
          <div style={{ display:"flex", gap:8 }}>
            <input className="input" placeholder="搜索候选人..." style={{ width:220 }} />
            <button className="btn-ghost">筛选</button>
          </div>
        </div>

        {/* 状态筛选 */}
        <div style={{ display:"flex", gap:8, marginBottom:16 }}>
          {[{key:"all",label:"全部"},{key:"pending",label:"待处理"},{key:"reviewing",label:"审核中"},{key:"interview",label:"面试中"},{key:"offer",label:"已发Offer"}].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)} style={{ padding:"6px 14px", borderRadius:100, fontSize:12, fontWeight:600, cursor:"pointer", border:"none", background:filter===f.key?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F8FAFC", color:filter===f.key?"white":"#64748B", boxShadow:filter===f.key?"0 2px 8px rgba(41,171,226,0.3)":"none" }}>{f.label}</button>
          ))}
        </div>

        {/* 候选人列表 */}
        <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
          {filtered.map((c,i) => {
            const st = STATUS_MAP[c.status];
            const sc = c.score >= 90 ? "#059669" : c.score >= 80 ? "#29ABE2" : "#D97706";
            const sb = c.score >= 90 ? "#ECFDF5" : c.score >= 80 ? "#EBF8FF" : "#FFFBEB";
            return (
              <div key={c.id} className="candidate-card fade-in" style={{ animationDelay:`${i*0.04}s`, border:selected?.id===c.id?"1.5px solid #29ABE2":"1px solid #F1F5F9" }} onClick={() => setSelected(selected?.id===c.id?null:c)}>
                <div style={{ display:"flex", gap:14, alignItems:"flex-start" }}>
                  <div style={{ width:48, height:48, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, fontWeight:800, color:"white", flexShrink:0 }}>{c.name[0]}</div>
                  <div style={{ flex:1 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:4 }}>
                      <div>
                        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                          <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B" }}>{c.name}</h3>
                          {c.verified && <span style={{ fontSize:10, fontWeight:700, color:"#059669", background:"#ECFDF5", padding:"1px 6px", borderRadius:100, border:"1px solid #A7F3D0" }}>✓ 已核验</span>}
                        </div>
                        <p style={{ fontSize:13, color:"#64748B" }}>{c.title} · {c.location} · {c.experience}</p>
                      </div>
                      <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:6 }}>
                        <span style={{ fontSize:13, fontWeight:800, color:sc, background:sb, padding:"3px 10px", borderRadius:100 }}>{c.score}% 匹配</span>
                        <span style={{ fontSize:11, fontWeight:700, color:st.color, background:st.bg, padding:"2px 8px", borderRadius:100 }}>{st.label}</span>
                      </div>
                    </div>
                    <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginTop:8 }}>
                      {c.skills.map(s => <span key={s} className="tag tag-blue" style={{ fontSize:11 }}>{s}</span>)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 候选人详情侧边栏 */}
      {selected && (
        <div className="card fade-in" style={{ padding:20, height:"fit-content", position:"sticky", top:84 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
            <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B" }}>候选人详情</h3>
            <button onClick={() => setSelected(null)} style={{ background:"none", border:"none", cursor:"pointer", color:"#94A3B8", fontSize:18 }}>×</button>
          </div>
          <div style={{ textAlign:"center", marginBottom:16 }}>
            <div style={{ width:64, height:64, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:24, fontWeight:800, color:"white", margin:"0 auto 10px" }}>{selected.name[0]}</div>
            <h2 style={{ fontSize:17, fontWeight:800, color:"#1E293B", marginBottom:2 }}>{selected.name}</h2>
            <p style={{ fontSize:13, color:"#64748B", marginBottom:8 }}>{selected.title}</p>
            <div style={{ display:"inline-flex", alignItems:"center", gap:4, background:"#ECFDF5", color:"#059669", padding:"4px 12px", borderRadius:100, fontSize:13, fontWeight:700 }}>
              {selected.score}% AI 匹配度
            </div>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:10, marginBottom:16 }}>
            {[{icon:"📍",label:"地点",value:selected.location},{icon:"⏱️",label:"经验",value:selected.experience},{icon:"💰",label:"期望薪资",value:selected.salary}].map(item => (
              <div key={item.label} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"8px 0", borderBottom:"1px solid #F1F5F9" }}>
                <span style={{ fontSize:13, color:"#64748B" }}>{item.icon} {item.label}</span>
                <span style={{ fontSize:13, fontWeight:600, color:"#1E293B" }}>{item.value}</span>
              </div>
            ))}
          </div>
          <div style={{ marginBottom:16 }}>
            <p style={{ fontSize:12, fontWeight:700, color:"#94A3B8", marginBottom:8, textTransform:"uppercase", letterSpacing:"0.05em" }}>技能标签</p>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {selected.skills.map(s => <span key={s} className="tag tag-blue">{s}</span>)}
            </div>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            <button className="btn-primary" style={{ width:"100%" }}>📅 邀请面试</button>
            <button className="btn-secondary" style={{ width:"100%" }}>💬 发送消息</button>
            <button className="btn-ghost" style={{ width:"100%" }}>🔍 查看完整简历</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default CandidatesPage;
