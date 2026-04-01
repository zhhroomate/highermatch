import React from "react";

export default function Billing() {
  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>账单管理</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>成功入职后付费，零风险招聘</p>
      </div>

      <div style={{ background: "#0A0A0A", borderRadius: 16, padding: 24, marginBottom: 20, color: "white" }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: "#A3A3A3", marginBottom: 8 }}>成功付费模式</p>
        <p style={{ fontSize: 15, color: "#D4D4D4", lineHeight: 1.7 }}>候选人通过试用期后系统自动触发账单。入职前不产生任何费用，真正的零风险招聘。</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12, marginBottom: 24 }}>
        {[
          { label: "已付款", value: "¥42K" },
          { label: "待付款", value: "¥18K" },
          { label: "试用期中", value: "6 人" },
        ].map((s, i) => (
          <div key={i} className="hm-card-flat" style={{ padding: 20 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: "#A3A3A3", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</p>
            <p style={{ fontSize: 24, fontWeight: 900, color: "#0A0A0A", letterSpacing: "-0.03em" }}>{s.value}</p>
          </div>
        ))}
      </div>

      <div className="hm-card-flat" style={{ overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #F5F5F5" }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: "#0A0A0A" }}>最近账单</h3>
        </div>
        {[
          { name: "李晓明 · 后端工程师", date: "2026-03-15", amount: "¥12,000", status: "已付款" },
          { name: "王芳 · 算法工程师", date: "2026-03-01", amount: "¥15,000", status: "试用期中" },
        ].map((b, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "14px 20px", borderBottom: "1px solid #F8F8F8" }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 14, fontWeight: 600, color: "#0A0A0A" }}>{b.name}</p>
              <p style={{ fontSize: 12, color: "#A3A3A3" }}>{b.date}</p>
            </div>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#0A0A0A" }}>{b.amount}</span>
            <span className={`hm-tag ${b.status === "已付款" ? "hm-tag-success" : "hm-tag-warning"}`}>{b.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
