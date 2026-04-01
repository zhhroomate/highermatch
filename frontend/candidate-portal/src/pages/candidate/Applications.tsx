import React from "react";

const APPS = [
  { job: "高级后端工程师", company: "字节跳动", status: "面试中", statusColor: "#0A0A0A", date: "3天前", stage: 3, total: 5 },
  { job: "推荐算法工程师", company: "阿里巴巴", status: "审核中", statusColor: "#737373", date: "1周前", stage: 2, total: 5 },
  { job: "前端架构师", company: "腾讯", status: "已投递", statusColor: "#A3A3A3", date: "2周前", stage: 1, total: 5 },
];

export default function Applications() {
  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>我的申请</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>{APPS.length} 个进行中的申请</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {APPS.map((a, i) => (
          <div key={i} className="hm-card-interactive" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A", marginBottom: 3 }}>{a.job}</h3>
                <p style={{ fontSize: 13, color: "#737373" }}>{a.company} · {a.date}</p>
              </div>
              <span className="hm-tag" style={{ background: a.statusColor === "#0A0A0A" ? "#0A0A0A" : "#F5F5F5", color: a.statusColor === "#0A0A0A" ? "white" : a.statusColor }}>{a.status}</span>
            </div>
            <div className="hm-progress" style={{ height: 3 }}>
              <div className="hm-progress-fill" style={{ width: `${(a.stage / a.total) * 100}%` }} />
            </div>
            <p style={{ fontSize: 11, color: "#A3A3A3", marginTop: 6 }}>进度 {a.stage}/{a.total}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
