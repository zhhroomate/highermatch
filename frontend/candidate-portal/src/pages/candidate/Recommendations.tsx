import React from "react";

const JOBS = [
  { title: "高级后端工程师", company: "字节跳动", salary: "30-40K", score: 96, tags: ["Go", "微服务", "K8s"], location: "北京", type: "全职" },
  { title: "推荐算法工程师", company: "阿里巴巴", salary: "35-50K", score: 93, tags: ["深度学习", "推荐系统"], location: "杭州", type: "全职" },
  { title: "前端架构师", company: "腾讯", salary: "40-55K", score: 89, tags: ["React", "TypeScript", "性能优化"], location: "深圳", type: "全职" },
  { title: "AI 产品经理", company: "美团", salary: "30-45K", score: 85, tags: ["AI", "产品设计", "数据分析"], location: "北京", type: "全职" },
];

export default function Recommendations() {
  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>为你推荐</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>基于你的技能和偏好，AI 精选最匹配的岗位</p>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {JOBS.map((j, i) => (
          <div key={i} className="hm-card-interactive" style={{ padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: "#0A0A0A", marginBottom: 4 }}>{j.title}</h3>
                <p style={{ fontSize: 13, color: "#737373" }}>{j.company} · {j.location} · {j.type}</p>
              </div>
              <div className="hm-score">{j.score}</div>
            </div>
            <p style={{ fontSize: 18, fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.02em", marginBottom: 10 }}>{j.salary}</p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {j.tags.map(t => <span key={t} className="hm-tag hm-tag-light">{t}</span>)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
