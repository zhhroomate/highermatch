import React, { useState } from "react";

interface BillingRecord { id:string; candidate:string; job:string; hireDate:string; trialEnd:string; status:string; amount:number; }

const MOCK: BillingRecord[] = [
  { id:"1", candidate:"郑华", job:"前端工程师", hireDate:"2026-01-15", trialEnd:"2026-04-15", status:"trial", amount:15000 },
  { id:"2", candidate:"吴刚", job:"后端工程师", hireDate:"2026-02-01", trialEnd:"2026-05-01", status:"pending", amount:18000 },
  { id:"3", candidate:"李明", job:"算法工程师", hireDate:"2025-11-01", trialEnd:"2026-02-01", status:"paid", amount:25000 },
  { id:"4", candidate:"张华", job:"产品经理", hireDate:"2025-12-15", trialEnd:"2026-03-15", status:"paid", amount:14000 },
];

const STATUS_MAP: Record<string, { label:string; color:string; bg:string; desc:string }> = {
  trial:   { label:"试用期中", color:"#29ABE2", bg:"#EBF8FF", desc:"试用期结束后自动触发付款" },
  pending: { label:"待付款", color:"#D97706", bg:"#FFFBEB", desc:"试用期已通过，请确认付款" },
  paid:    { label:"已付款", color:"#059669", bg:"#ECFDF5", desc:"入职成功，款项已结清" },
};

const BillingPage: React.FC = () => {
  const [records] = useState<BillingRecord[]>(MOCK);
  const totalPaid = records.filter(r=>r.status==="paid").reduce((a,r)=>a+r.amount,0);
  const totalPending = records.filter(r=>r.status==="pending").reduce((a,r)=>a+r.amount,0);

  return (
    <div className="fade-in">
      <div style={{ marginBottom:24 }}>
        <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", marginBottom:4 }}>账单管理</h1>
        <p style={{ fontSize:14, color:"#64748B" }}>成功入职后付费，试用期通过才触发账单</p>
      </div>

      {/* 说明卡片 */}
      <div style={{ background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", borderRadius:16, padding:"16px 20px", marginBottom:20, border:"1.5px solid #B3E0F5" }}>
        <div style={{ display:"flex", alignItems:"flex-start", gap:12 }}>
          <div style={{ width:40, height:40, borderRadius:10, background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, flexShrink:0 }}>💡</div>
          <div>
            <p style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:4 }}>成功付费模式</p>
            <p style={{ fontSize:13, color:"#64748B", lineHeight:1.6 }}>我们采用「入职成功后付费」模式：候选人通过试用期（通常 3 个月）后，系统自动触发账单。您无需承担无效招聘的费用风险。</p>
          </div>
        </div>
      </div>

      {/* 统计 */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:16, marginBottom:24 }}>
        {[
          {label:"已付款",value:`¥${(totalPaid/1000).toFixed(1)}K`,color:"#059669",bg:"#ECFDF5",icon:"✅"},
          {label:"待付款",value:`¥${(totalPending/1000).toFixed(1)}K`,color:"#D97706",bg:"#FFFBEB",icon:"⏳"},
          {label:"试用期中",value:`${records.filter(r=>r.status==="trial").length} 人`,color:"#29ABE2",bg:"#EBF8FF",icon:"🔄"},
        ].map(s => (
          <div key={s.label} className="stat-card" style={{ padding:16 }}>
            <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
              <span style={{ fontSize:20 }}>{s.icon}</span>
              <span style={{ fontSize:12, color:"#64748B", fontWeight:600 }}>{s.label}</span>
            </div>
            <p style={{ fontSize:22, fontWeight:800, color:s.color }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* 账单列表 */}
      <div className="card" style={{ overflow:"hidden" }}>
        <div style={{ padding:"16px 20px", borderBottom:"1px solid #F1F5F9" }}>
          <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B" }}>账单记录</h3>
        </div>
        <table className="data-table">
          <thead>
            <tr><th>候选人</th><th>岗位</th><th>入职日期</th><th>试用期截止</th><th>状态</th><th>金额</th><th>操作</th></tr>
          </thead>
          <tbody>
            {records.map(r => {
              const st = STATUS_MAP[r.status];
              return (
                <tr key={r.id}>
                  <td>
                    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                      <div style={{ width:32, height:32, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, fontWeight:800, color:"white", flexShrink:0 }}>{r.candidate[0]}</div>
                      <span style={{ fontWeight:700, color:"#1E293B" }}>{r.candidate}</span>
                    </div>
                  </td>
                  <td style={{ color:"#64748B" }}>{r.job}</td>
                  <td style={{ color:"#64748B" }}>{r.hireDate}</td>
                  <td style={{ color:"#64748B" }}>{r.trialEnd}</td>
                  <td>
                    <div>
                      <span style={{ fontSize:12, fontWeight:700, color:st.color, background:st.bg, padding:"3px 10px", borderRadius:100 }}>{st.label}</span>
                      <p style={{ fontSize:11, color:"#94A3B8", marginTop:2 }}>{st.desc}</p>
                    </div>
                  </td>
                  <td><span style={{ fontSize:14, fontWeight:800, color:r.status==="paid"?"#059669":"#1E293B" }}>¥{r.amount.toLocaleString()}</span></td>
                  <td>
                    {r.status === "pending" ? (
                      <button className="btn-primary" style={{ padding:"6px 14px", fontSize:12 }}>确认付款</button>
                    ) : (
                      <button className="btn-ghost" style={{ padding:"5px 10px", fontSize:12 }}>查看详情</button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BillingPage;
