import React, { useState } from "react";

interface PipelineCard { id:string; name:string; title:string; score:number; company?:string; date:string; }
interface PipelineCol { id:string; label:string; color:string; bg:string; cards:PipelineCard[]; }

const INIT_COLS: PipelineCol[] = [
  { id:"applied", label:"已申请", color:"#64748B", bg:"#F8FAFC", cards:[
    { id:"1", name:"李晓明", title:"高级后端工程师", score:96, date:"2天前" },
    { id:"2", name:"王芳", title:"推荐算法工程师", score:91, date:"3天前" },
    { id:"3", name:"刘洋", title:"数据分析师", score:79, date:"5天前" },
  ]},
  { id:"screening", label:"简历筛选", color:"#29ABE2", bg:"#EBF8FF", cards:[
    { id:"4", name:"陈静", title:"产品经理", score:84, date:"1天前" },
    { id:"5", name:"赵磊", title:"前端工程师", score:88, date:"2天前" },
  ]},
  { id:"interview", label:"面试中", color:"#7C3AED", bg:"#F5F3FF", cards:[
    { id:"6", name:"孙明", title:"架构师", score:93, date:"今天" },
    { id:"7", name:"周婷", title:"算法工程师", score:89, date:"昨天" },
  ]},
  { id:"offer", label:"已发Offer", color:"#059669", bg:"#ECFDF5", cards:[
    { id:"8", name:"吴刚", title:"后端工程师", score:91, date:"3天前" },
  ]},
  { id:"hired", label:"已入职", color:"#D97706", bg:"#FFFBEB", cards:[
    { id:"9", name:"郑华", title:"前端工程师", score:87, date:"2周前" },
  ]},
];

const PipelinePage: React.FC = () => {
  const [cols] = useState<PipelineCol[]>(INIT_COLS);

  return (
    <div className="fade-in">
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:24 }}>
        <div>
          <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:4 }}>招聘管道</h1>
          <p style={{ fontSize:14, color:"#64748B" }}>可视化追踪每位候选人的招聘进度</p>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <button className="btn-ghost">
            <svg viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3"/></svg>
            筛选
          </button>
          <button className="btn-primary">导出报告</button>
        </div>
      </div>

      {/* 统计 */}
      <div style={{ display:"flex", gap:12, marginBottom:20, overflowX:"auto", paddingBottom:4 }}>
        {cols.map(col => (
          <div key={col.id} style={{ background:col.bg, borderRadius:12, padding:"10px 16px", flexShrink:0, border:`1px solid ${col.color}22` }}>
            <p style={{ fontSize:20, fontWeight:800, color:col.color }}>{col.cards.length}</p>
            <p style={{ fontSize:12, color:"#64748B", fontWeight:600 }}>{col.label}</p>
          </div>
        ))}
      </div>

      {/* 看板 */}
      <div style={{ display:"flex", gap:14, overflowX:"auto", paddingBottom:16 }}>
        {cols.map(col => (
          <div key={col.id} className="pipeline-col">
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                <div style={{ width:8, height:8, borderRadius:"50%", background:col.color }} />
                <span style={{ fontSize:13, fontWeight:700, color:"#1E293B" }}>{col.label}</span>
              </div>
              <span style={{ fontSize:12, fontWeight:700, color:col.color, background:col.bg, padding:"2px 8px", borderRadius:100, border:`1px solid ${col.color}33` }}>{col.cards.length}</span>
            </div>
            {col.cards.map(card => {
              const sc = card.score >= 90 ? "#059669" : card.score >= 80 ? "#29ABE2" : "#D97706";
              return (
                <div key={card.id} className="pipeline-card">
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
                    <div style={{ width:32, height:32, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, fontWeight:800, color:"white", flexShrink:0 }}>{card.name[0]}</div>
                    <div style={{ flex:1, minWidth:0 }}>
                      <p style={{ fontSize:13, fontWeight:700, color:"#1E293B", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{card.name}</p>
                      <p style={{ fontSize:11, color:"#64748B", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{card.title}</p>
                    </div>
                  </div>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                    <span style={{ fontSize:11, fontWeight:700, color:sc }}>{card.score}% 匹配</span>
                    <span style={{ fontSize:10, color:"#94A3B8" }}>{card.date}</span>
                  </div>
                </div>
              );
            })}
            <button style={{ width:"100%", padding:"8px", borderRadius:8, background:"transparent", border:"1.5px dashed #E2E8F0", color:"#94A3B8", fontSize:12, fontWeight:600, cursor:"pointer", marginTop:4 }}>+ 添加</button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PipelinePage;
