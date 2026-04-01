import React from "react";

const JOBS = [
  { title: "高级后端工程师", dept: "技术部", apps: 24, status: "active", posted: "3天前" },
  { title: "推荐算法工程师", dept: "算法组", apps: 18, status: "active", posted: "1周前" },
  { title: "前端架构师", dept: "技术部", apps: 31, status: "active", posted: "2周前" },
  { title: "产品经理", dept: "产品部", apps: 12, status: "paused", posted: "1月前" },
];

export default function Jobs() {
  return (
    <div className="hm-fade-in">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>职位管理</h1>
          <p style={{ fontSize: 14, color: "#A3A3A3" }}>{JOBS.length} 个职位</p>
        </div>
        <button className="hm-btn hm-btn-primary">+ 发布新职位</button>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {JOBS.map((j, i) => (
          <div key={i} className="hm-card-interactive" style={{ padding: 20, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A", marginBottom: 3 }}>{j.title}</h3>
              <p style={{ fontSize: 13, color: "#A3A3A3" }}>{j.dept} · {j.posted}</p>
            </div>
            <div style={{ textAlign: "center", minWidth: 60 }}>
              <p style={{ fontSize: 20, fontWeight: 800, color: "#0A0A0A" }}>{j.apps}</p>
              <p style={{ fontSize: 11, color: "#A3A3A3" }}>申请</p>
            </div>
            <span className={`hm-tag ${j.status === "active" ? "hm-tag-dark" : "hm-tag-light"}`}>
              {j.status === "active" ? "招聘中" : "已暂停"}
            </span>
            <button className="hm-btn hm-btn-ghost hm-btn-sm">编辑</button>
          </div>
        ))}
      </div>
    </div>
  );
}
