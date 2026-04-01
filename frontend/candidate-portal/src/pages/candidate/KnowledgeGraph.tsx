import React, { useState } from "react";

const NODES = [
  { id: "me", label: "我", x: 50, y: 50, size: 24, color: "#0A0A0A" },
  { id: "go", label: "Go", x: 25, y: 25, size: 16, color: "#404040" },
  { id: "python", label: "Python", x: 75, y: 20, size: 16, color: "#404040" },
  { id: "k8s", label: "K8s", x: 15, y: 55, size: 14, color: "#737373" },
  { id: "micro", label: "微服务", x: 35, y: 75, size: 14, color: "#737373" },
  { id: "backend", label: "后端工程师", x: 80, y: 45, size: 18, color: "#262626" },
  { id: "arch", label: "架构师", x: 70, y: 75, size: 16, color: "#525252" },
  { id: "ai", label: "AI工程师", x: 85, y: 70, size: 14, color: "#737373" },
];

const EDGES = [
  ["me", "go"], ["me", "python"], ["me", "k8s"], ["me", "micro"],
  ["go", "backend"], ["python", "backend"], ["python", "ai"],
  ["k8s", "backend"], ["micro", "arch"], ["backend", "arch"],
];

export default function KnowledgeGraph() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>技能图谱</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>技能、行业、岗位的关联关系可视化</p>
      </div>

      <div className="hm-card-flat" style={{ padding: 20, marginBottom: 16 }}>
        <svg viewBox="0 0 100 100" style={{ width: "100%", height: "auto", minHeight: 280 }}>
          {EDGES.map(([from, to], i) => {
            const a = NODES.find(n => n.id === from)!;
            const b = NODES.find(n => n.id === to)!;
            const highlight = selected === from || selected === to;
            return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={highlight ? "#0A0A0A" : "#E5E5E5"} strokeWidth={highlight ? 0.6 : 0.3} />;
          })}
          {NODES.map(n => (
            <g key={n.id} onClick={() => setSelected(selected === n.id ? null : n.id)} style={{ cursor: "pointer" }}>
              <circle cx={n.x} cy={n.y} r={n.size / 6} fill={selected === n.id ? "#0A0A0A" : n.color} opacity={selected && selected !== n.id ? 0.3 : 1} />
              <text x={n.x} y={n.y + n.size / 6 + 4} textAnchor="middle" fontSize="3" fill={selected === n.id ? "#0A0A0A" : "#737373"} fontWeight={selected === n.id ? "700" : "500"}>{n.label}</text>
            </g>
          ))}
        </svg>
      </div>

      <div className="hm-card-flat" style={{ padding: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0A0A0A", marginBottom: 12 }}>数据核验状态</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[
            { label: "学历认证", status: "已核验", ok: true },
            { label: "工作经历", status: "已核验", ok: true },
            { label: "技能证书", status: "待核验", ok: false },
          ].map((v, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0" }}>
              <span style={{ fontSize: 14, color: "#404040" }}>{v.label}</span>
              <span className={`hm-tag ${v.ok ? "hm-tag-success" : "hm-tag-warning"}`}>{v.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
