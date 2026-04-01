import React from "react";

export default function Analytics() {
  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>人才洞察</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>基于平台数据的行业人才分析报告</p>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "平均薪资", value: "¥28K", sub: "同比 +12%" },
          { label: "人才流动率", value: "18%", sub: "环比 -3%" },
          { label: "岗位竞争度", value: "1:8", sub: "8人竞争1岗" },
          { label: "平均招聘周期", value: "23天", sub: "行业均值 35天" },
        ].map((s, i) => (
          <div key={i} className="hm-card-flat" style={{ padding: 24 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: "#A3A3A3", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</p>
            <p style={{ fontSize: 32, fontWeight: 900, color: "#0A0A0A", letterSpacing: "-0.03em" }}>{s.value}</p>
            <p style={{ fontSize: 12, color: "#737373", marginTop: 6 }}>{s.sub}</p>
          </div>
        ))}
      </div>
      <div className="hm-card-flat" style={{ padding: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A", marginBottom: 16 }}>热门技能需求 TOP 5</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            { skill: "大模型 / LLM", pct: 92 },
            { skill: "Go / Rust", pct: 78 },
            { skill: "Kubernetes", pct: 71 },
            { skill: "推荐系统", pct: 65 },
            { skill: "React / TypeScript", pct: 58 },
          ].map((s, i) => (
            <div key={i}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#404040" }}>{s.skill}</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "#0A0A0A" }}>{s.pct}%</span>
              </div>
              <div className="hm-progress"><div className="hm-progress-fill" style={{ width: `${s.pct}%` }} /></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
