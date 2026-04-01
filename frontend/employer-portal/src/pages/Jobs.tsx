import React, { useState } from "react";

interface Job { id:string; title:string; department:string; location:string; type:string; status:string; applicants:number; matched:number; posted:string; salary:string; }

const MOCK_JOBS: Job[] = [
  { id:"1", title:"高级后端工程师", department:"技术部", location:"北京", type:"全职", status:"active", applicants:87, matched:12, posted:"3天前", salary:"35-50K" },
  { id:"2", title:"推荐算法工程师", department:"AI 部", location:"杭州", type:"全职", status:"active", applicants:64, matched:8, posted:"1周前", salary:"40-60K" },
  { id:"3", title:"前端工程师", department:"技术部", location:"深圳", type:"全职", status:"paused", applicants:43, matched:6, posted:"2周前", salary:"25-40K" },
  { id:"4", title:"产品经理", department:"产品部", location:"北京", type:"全职", status:"active", applicants:112, matched:15, posted:"5天前", salary:"20-35K" },
  { id:"5", title:"数据分析师", department:"数据部", location:"上海", type:"全职", status:"closed", applicants:56, matched:9, posted:"1个月前", salary:"18-28K" },
];

const STATUS_MAP: Record<string, { label:string; color:string; bg:string }> = {
  active: { label:"招聘中", color:"#059669", bg:"#ECFDF5" },
  paused: { label:"已暂停", color:"#D97706", bg:"#FFFBEB" },
  closed: { label:"已关闭", color:"#94A3B8", bg:"#F8FAFC" },
};

const JobsPage: React.FC = () => {
  const [jobs] = useState<Job[]>(MOCK_JOBS);
  const [showModal, setShowModal] = useState(false);
  const [voiceMode, setVoiceMode] = useState(false);
  const [recording, setRecording] = useState(false);

  return (
    <div className="fade-in">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:24 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:4 }}>职位管理</h1>
          <p style={{ fontSize:14, color:"#64748B" }}>管理所有在招职位，AI 自动匹配候选人</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          发布职位
        </button>
      </div>

      {/* 统计 */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14, marginBottom:20 }}>
        {[{label:"在招职位",value:jobs.filter(j=>j.status==="active").length,color:"#059669",bg:"#ECFDF5"},{label:"总申请数",value:jobs.reduce((a,j)=>a+j.applicants,0),color:"#29ABE2",bg:"#EBF8FF"},{label:"AI 匹配",value:jobs.reduce((a,j)=>a+j.matched,0),color:"#7C3AED",bg:"#F5F3FF"}].map(s => (
          <div key={s.label} className="stat-card" style={{ padding:16 }}>
            <p style={{ fontSize:24, fontWeight:800, color:s.color, marginBottom:2 }}>{s.value}</p>
            <p style={{ fontSize:13, color:"#64748B" }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* 职位列表 */}
      <div className="card" style={{ overflow:"hidden" }}>
        <div style={{ padding:"16px 20px", borderBottom:"1px solid #F1F5F9", display:"flex", alignItems:"center", gap:12 }}>
          <input className="input" placeholder="搜索职位名称..." style={{ maxWidth:280 }} />
          <button className="btn-ghost">全部状态</button>
          <button className="btn-ghost">全部部门</button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>职位名称</th><th>部门</th><th>地点</th><th>薪资</th>
              <th>申请数</th><th>AI 匹配</th><th>状态</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map(job => {
              const st = STATUS_MAP[job.status];
              return (
                <tr key={job.id}>
                  <td>
                    <div>
                      <p style={{ fontWeight:700, color:"#1E293B" }}>{job.title}</p>
                      <p style={{ fontSize:12, color:"#94A3B8" }}>{job.posted}发布</p>
                    </div>
                  </td>
                  <td><span className="tag tag-blue">{job.department}</span></td>
                  <td style={{ color:"#64748B" }}>{job.location}</td>
                  <td style={{ fontWeight:700, color:"#059669" }}>{job.salary}</td>
                  <td>
                    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                      <span style={{ fontWeight:700, color:"#1E293B" }}>{job.applicants}</span>
                      <span style={{ fontSize:11, color:"#94A3B8" }}>人</span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                      <span style={{ fontWeight:700, color:"#7C3AED" }}>{job.matched}</span>
                      <span style={{ fontSize:11, color:"#94A3B8" }}>精准匹配</span>
                    </div>
                  </td>
                  <td><span style={{ fontSize:12, fontWeight:700, color:st.color, background:st.bg, padding:"3px 10px", borderRadius:100 }}>{st.label}</span></td>
                  <td>
                    <div style={{ display:"flex", gap:6 }}>
                      <button className="btn-ghost" style={{ padding:"5px 10px", fontSize:12 }}>查看</button>
                      <button className="btn-ghost" style={{ padding:"5px 10px", fontSize:12 }}>编辑</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 发布职位弹窗 */}
      {showModal && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.4)", zIndex:200, display:"flex", alignItems:"center", justifyContent:"center", padding:20 }}>
          <div style={{ background:"white", borderRadius:20, width:"100%", maxWidth:560, maxHeight:"90vh", overflow:"auto" }}>
            <div style={{ padding:"20px 24px", borderBottom:"1px solid #F1F5F9", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <h2 style={{ fontSize:18, fontWeight:800, color:"#1E293B" }}>发布新职位</h2>
              <button onClick={() => setShowModal(false)} style={{ background:"none", border:"none", cursor:"pointer", fontSize:20, color:"#94A3B8" }}>×</button>
            </div>
            <div style={{ padding:"20px 24px" }}>
              {/* 语音/文字切换 */}
              <div style={{ display:"flex", gap:8, marginBottom:20 }}>
                <button onClick={() => setVoiceMode(false)} style={{ flex:1, padding:"10px", borderRadius:10, border:"none", cursor:"pointer", background:!voiceMode?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F8FAFC", color:!voiceMode?"white":"#64748B", fontWeight:700, fontSize:13 }}>✏️ 文字描述</button>
                <button onClick={() => setVoiceMode(true)} style={{ flex:1, padding:"10px", borderRadius:10, border:"none", cursor:"pointer", background:voiceMode?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F8FAFC", color:voiceMode?"white":"#64748B", fontWeight:700, fontSize:13 }}>🎙️ 语音描述</button>
              </div>

              {voiceMode ? (
                <div style={{ textAlign:"center", padding:"30px 0" }}>
                  <p style={{ fontSize:14, color:"#64748B", marginBottom:20 }}>用语音描述你的招聘需求，AI 自动生成职位详情</p>
                  <button onClick={() => setRecording(!recording)} style={{ width:80, height:80, borderRadius:"50%", background:recording?"linear-gradient(135deg,#EF4444,#DC2626)":"linear-gradient(135deg,#29ABE2,#1A8FBF)", border:"none", cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 16px", boxShadow:recording?"0 8px 24px rgba(239,68,68,0.4)":"0 8px 24px rgba(41,171,226,0.4)" }}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:28, height:28 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
                  </button>
                  <p style={{ fontSize:13, color:recording?"#EF4444":"#94A3B8", fontWeight:recording?700:400 }}>{recording?"正在录音，点击停止...":"点击开始语音描述"}</p>
                </div>
              ) : (
                <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
                  {[{label:"职位名称",placeholder:"如：高级后端工程师"},{label:"所属部门",placeholder:"如：技术部"},{label:"工作地点",placeholder:"如：北京"},{label:"薪资范围",placeholder:"如：35-50K"}].map(f => (
                    <div key={f.label}>
                      <label style={{ fontSize:13, fontWeight:600, color:"#475569", display:"block", marginBottom:6 }}>{f.label}</label>
                      <input className="input" placeholder={f.placeholder} />
                    </div>
                  ))}
                  <div>
                    <label style={{ fontSize:13, fontWeight:600, color:"#475569", display:"block", marginBottom:6 }}>职位描述</label>
                    <textarea className="input" placeholder="描述职位职责、要求和福利..." rows={4} style={{ resize:"vertical" }} />
                  </div>
                </div>
              )}

              <div style={{ display:"flex", gap:10, marginTop:20 }}>
                <button className="btn-ghost" style={{ flex:1 }} onClick={() => setShowModal(false)}>取消</button>
                <button className="btn-primary" style={{ flex:2 }}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
                  AI 生成并发布
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobsPage;
