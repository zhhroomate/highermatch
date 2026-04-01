import React from "react";

const CANDIDATES = [
  { name: "李晓明", role: "高级后端工程师", score: 96, verify: true, status: "面试中" },
  { name: "王芳", role: "推荐算法工程师", score: 91, verify: true, status: "审核中" },
  { name: "张伟", role: "前端架构师", score: 88, verify: false, status: "待处理" },
  { name: "陈静", role: "产品经理", score: 84, verify: true, status: "已发Offer" },
];

export default function Candidates() {
  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>候选人库</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>{CANDIDATES.length} 位候选人</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {CANDIDATES.map((c, i) => (
          <div key={i} className="hm-card-interactive" style={{ padding: 20, display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
            <div className="hm-avatar hm-avatar-lg" style={{ background: "#0A0A0A", color: "white" }}>{c.name[0]}</div>
            <div style={{ flex: 1, minWidth: 160 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                <p style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A" }}>{c.name}</p>
                {c.verify && <span className="hm-tag hm-tag-success" style={{ fontSize: 10, padding: "2px 8px" }}>已核验</span>}
              </div>
              <p style={{ fontSize: 13, color: "#737373" }}>{c.role}</p>
            </div>
            <div className="hm-score">{c.score}</div>
            <span className="hm-tag hm-tag-light">{c.status}</span>
            <button className="hm-btn hm-btn-ghost hm-btn-sm">详情</button>
          </div>
        ))}
      </div>
    </div>
  );
}
