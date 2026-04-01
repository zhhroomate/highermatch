import React, { useState } from "react";
import { useLocation } from "wouter";

const FEATURES = [
  { icon: "🎙", title: "语音即简历", desc: "开口描述，AI 自动生成结构化简历，告别繁琐填表" },
  { icon: "🎯", title: "精准匹配", desc: "基于深度学习的人岗匹配引擎，匹配度高达 96%" },
  { icon: "🔍", title: "多源核验", desc: "学历、工作经历、技能证书全方位数据交叉验证" },
  { icon: "🧠", title: "知识图谱", desc: "技能-行业-岗位关联图谱，发现隐藏的职业机会" },
  { icon: "💬", title: "职场社区", desc: "关注同行、分享经验、拓展人脉的职场社交圈" },
  { icon: "💎", title: "成功付费", desc: "候选人入职并通过试用期后才付费，零风险招聘" },
];

const STATS = [
  { value: "50万+", label: "活跃求职者" },
  { value: "2万+", label: "合作企业" },
  { value: "96%", label: "匹配满意度" },
  { value: "72h", label: "平均入职周期" },
];

export default function LandingPage() {
  const [, navigate] = useLocation();

  return (
    <div style={{ minHeight: "100vh", background: "#FAFAFA" }}>
      {/* 导航 */}
      <nav className="hm-topnav">
        <a href="/" className="hm-topnav-logo">
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "#0A0A0A", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
          </div>
          HigherMatch
        </a>
        <div className="hm-topnav-links hm-hide-mobile">
          <a href="#features" className="hm-topnav-link">功能</a>
          <a href="#community" className="hm-topnav-link">社区</a>
          <a href="#pricing" className="hm-topnav-link">定价</a>
        </div>
        <div className="hm-topnav-actions">
          <button className="hm-btn hm-btn-ghost hm-btn-sm" onClick={() => navigate("/candidate")}>求职者</button>
          <button className="hm-btn hm-btn-primary hm-btn-sm" onClick={() => navigate("/employer")}>企业招聘</button>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: "clamp(60px,12vh,120px) clamp(16px,4vw,48px) clamp(40px,8vh,80px)", maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 48, alignItems: "center" }} className="hero-grid">
          <div className="hm-fade-in">
            <div className="hm-tag hm-tag-dark" style={{ marginBottom: 24 }}>AI 驱动 · 颠覆式招聘</div>
            <h1 style={{ fontSize: "clamp(36px,5vw,64px)", fontWeight: 900, lineHeight: 1.05, letterSpacing: "-0.04em", color: "#0A0A0A", marginBottom: 20 }}>
              开口即结果<br/>
              <span style={{ color: "#A3A3A3" }}>交付即匹配</span>
            </h1>
            <p style={{ fontSize: "clamp(16px,1.8vw,20px)", color: "#737373", lineHeight: 1.7, maxWidth: 520, marginBottom: 36 }}>
              以语音交互为入口，AI Agent 为中枢，重构招聘全流程。求职者告别填表，雇主告别筛选，精准匹配从此开始。
            </p>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <button className="hm-btn hm-btn-primary hm-btn-lg" onClick={() => navigate("/candidate")}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 18, height: 18 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
                我要找工作
              </button>
              <button className="hm-btn hm-btn-secondary hm-btn-lg" onClick={() => navigate("/employer")}>
                我要招人才 →
              </button>
            </div>
          </div>
        </div>

        {/* 数据统计 */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 1, background: "#E5E5E5", borderRadius: 16, overflow: "hidden", marginTop: 64 }} className="hm-fade-in">
          {STATS.map((s, i) => (
            <div key={i} style={{ background: "white", padding: "28px 24px", textAlign: "center" }}>
              <p style={{ fontSize: "clamp(24px,3vw,36px)", fontWeight: 900, color: "#0A0A0A", letterSpacing: "-0.03em" }}>{s.value}</p>
              <p style={{ fontSize: 13, color: "#A3A3A3", marginTop: 4, fontWeight: 500 }}>{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 功能特性 */}
      <section id="features" style={{ padding: "80px clamp(16px,4vw,48px)", maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <h2 style={{ fontSize: "clamp(28px,3.5vw,42px)", fontWeight: 800, letterSpacing: "-0.03em", color: "#0A0A0A", marginBottom: 12 }}>重新定义招聘</h2>
          <p style={{ fontSize: 16, color: "#A3A3A3", maxWidth: 480, margin: "0 auto" }}>六大核心能力，构建全流程自动化招聘操作系统</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))", gap: 16 }}>
          {FEATURES.map((f, i) => (
            <div key={i} className="hm-card-interactive" style={{ padding: 28 }}>
              <span style={{ fontSize: 28, display: "block", marginBottom: 16 }}>{f.icon}</span>
              <h3 style={{ fontSize: 17, fontWeight: 700, color: "#0A0A0A", marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 14, color: "#737373", lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 社区预览 */}
      <section id="community" style={{ padding: "80px clamp(16px,4vw,48px)", background: "#0A0A0A" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", textAlign: "center" }}>
          <h2 style={{ fontSize: "clamp(28px,3.5vw,42px)", fontWeight: 800, letterSpacing: "-0.03em", color: "white", marginBottom: 12 }}>职场社区</h2>
          <p style={{ fontSize: 16, color: "#737373", maxWidth: 480, margin: "0 auto 48px" }}>不只是招聘，更是职场人脉与知识的连接</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, maxWidth: 800, margin: "0 auto" }}>
            {[
              { icon: "✍️", title: "分享经验", desc: "发帖分享职场心得与行业见解" },
              { icon: "🤝", title: "拓展人脉", desc: "关注同行，发现潜在合作伙伴" },
              { icon: "💡", title: "获取洞察", desc: "行业趋势、薪资报告一手掌握" },
            ].map((item, i) => (
              <div key={i} style={{ background: "#171717", borderRadius: 16, padding: 28, border: "1px solid #262626" }}>
                <span style={{ fontSize: 28, display: "block", marginBottom: 12 }}>{item.icon}</span>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: "white", marginBottom: 6 }}>{item.title}</h3>
                <p style={{ fontSize: 13, color: "#737373", lineHeight: 1.5 }}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 定价 */}
      <section id="pricing" style={{ padding: "80px clamp(16px,4vw,48px)", maxWidth: 1200, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <h2 style={{ fontSize: "clamp(28px,3.5vw,42px)", fontWeight: 800, letterSpacing: "-0.03em", color: "#0A0A0A", marginBottom: 12 }}>透明定价</h2>
          <p style={{ fontSize: 16, color: "#A3A3A3" }}>成功入职后才付费，零风险</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 16, maxWidth: 900, margin: "0 auto" }}>
          {[
            { name: "基础版", price: "免费", desc: "适合初创团队", features: ["AI 智能匹配", "每月 5 个岗位", "基础数据报告", "社区访问"] },
            { name: "专业版", price: "¥999/月", desc: "适合成长型企业", features: ["无限岗位发布", "高级 AI 推荐", "多源数据核验", "人才洞察报告", "优先客服支持"], featured: true },
            { name: "企业版", price: "定制", desc: "适合大型企业", features: ["全部专业版功能", "API 接入", "专属客户经理", "定制化报告", "SLA 保障"] },
          ].map((plan, i) => (
            <div key={i} style={{ background: plan.featured ? "#0A0A0A" : "white", borderRadius: 20, padding: 32, border: plan.featured ? "none" : "1px solid #E5E5E5", position: "relative" }}>
              {plan.featured && <div style={{ position: "absolute", top: -10, left: "50%", transform: "translateX(-50%)" }}><span className="hm-tag" style={{ background: "white", color: "#0A0A0A", fontSize: 11 }}>最受欢迎</span></div>}
              <h3 style={{ fontSize: 18, fontWeight: 700, color: plan.featured ? "white" : "#0A0A0A", marginBottom: 4 }}>{plan.name}</h3>
              <p style={{ fontSize: 13, color: plan.featured ? "#737373" : "#A3A3A3", marginBottom: 16 }}>{plan.desc}</p>
              <p style={{ fontSize: 32, fontWeight: 900, color: plan.featured ? "white" : "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 24 }}>{plan.price}</p>
              <ul style={{ listStyle: "none", padding: 0, marginBottom: 24 }}>
                {plan.features.map((f, j) => (
                  <li key={j} style={{ fontSize: 14, color: plan.featured ? "#A3A3A3" : "#737373", padding: "6px 0", display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ color: plan.featured ? "white" : "#0A0A0A" }}>✓</span> {f}
                  </li>
                ))}
              </ul>
              <button className={`hm-btn ${plan.featured ? "hm-btn-secondary" : "hm-btn-primary"}`} style={{ width: "100%" }}>
                {plan.price === "定制" ? "联系我们" : "立即开始"}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid #E5E5E5", padding: "40px clamp(16px,4vw,48px)", textAlign: "center" }}>
        <p style={{ fontSize: 13, color: "#A3A3A3" }}>© 2026 HigherMatch. 用技术重构价值，用体验赢得用户。</p>
      </footer>

      <style>{`
        @media (min-width: 768px) {
          .hero-grid { grid-template-columns: 1fr !important; }
        }
        @media (max-width: 767px) {
          .hm-topnav { display: flex !important; padding: 0 16px; }
          .hm-topnav-links { display: none !important; }
          section#features > div:last-child { grid-template-columns: 1fr !important; }
          section#community > div > div:last-child { grid-template-columns: 1fr !important; }
          section#pricing > div:last-child { grid-template-columns: 1fr !important; }
          div[style*="grid-template-columns: repeat(4"] { grid-template-columns: repeat(2, 1fr) !important; }
        }
      `}</style>
    </div>
  );
}
