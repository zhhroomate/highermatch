import React from "react";

const STAGES = [
  { name: "待处理", count: 12, items: ["李明", "王芳", "张伟"] },
  { name: "审核中", count: 8, items: ["陈静", "赵一"] },
  { name: "面试中", count: 5, items: ["周婷"] },
  { name: "已发Offer", count: 3, items: ["林雨"] },
  { name: "已入职", count: 2, items: ["刘强"] },
];

export default function Pipeline() {
  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>招聘管道</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>可视化招聘流程</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12 }}>
        {STAGES.map((s, i) => (
          <div key={i} className="hm-card-flat" style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#737373" }}>{s.name}</span>
              <span style={{ fontSize: 18, fontWeight: 900, color: "#0A0A0A" }}>{s.count}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {s.items.map((name, j) => (
                <div key={j} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", background: "#F8F8F8", borderRadius: 8 }}>
                  <div className="hm-avatar hm-avatar-sm" style={{ background: "#0A0A0A", color: "white" }}>{name[0]}</div>
                  <span style={{ fontSize: 13, fontWeight: 500, color: "#404040" }}>{name}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
