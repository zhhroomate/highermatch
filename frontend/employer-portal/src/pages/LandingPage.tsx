import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [recording, setRecording] = useState(false);
  const [demoText, setDemoText] = useState("");
  const demoTexts = [
    "我需要招聘一名高级后端工程师，要求 5 年以上经验，熟悉 Python 和 Go，有分布式系统经验...",
    "我们在找一位推荐算法工程师，需要有机器学习背景，熟悉 Spark 和 TensorFlow...",
    "招聘产品经理，负责 B 端 SaaS 产品，需要有 3 年以上产品经验...",
  ];
  let demoIdx = 0;

  const startDemo = () => {
    setRecording(true);
    setDemoText("");
    const text = demoTexts[demoIdx % demoTexts.length];
    demoIdx++;
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDemoText(text.slice(0, i + 1));
        i++;
      } else {
        clearInterval(interval);
        setTimeout(() => setRecording(false), 500);
      }
    }, 40);
  };

  return (
    <div style={{ minHeight:"100vh", background:"#F5F8FF", fontFamily:"'Plus Jakarta Sans',sans-serif" }}>
      {/* 导航栏 */}
      <nav style={{ background:"rgba(255,255,255,0.9)", backdropFilter:"blur(12px)", borderBottom:"1px solid #F1F5F9", padding:"0 40px", height:64, display:"flex", alignItems:"center", justifyContent:"space-between", position:"sticky", top:0, zIndex:100 }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:36, height:36, borderRadius:10, background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
          </div>
          <span style={{ fontSize:18, fontWeight:800, color:"#1E293B" }}>HigherMatch</span>
        </div>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <a href="#features" style={{ fontSize:14, color:"#64748B", textDecoration:"none", fontWeight:500 }}>功能特性</a>
          <a href="#pricing" style={{ fontSize:14, color:"#64748B", textDecoration:"none", fontWeight:500 }}>定价</a>
          <button onClick={() => navigate("/dashboard")} style={{ padding:"8px 20px", borderRadius:10, background:"linear-gradient(135deg,#29ABE2,#1A8FBF)", color:"white", fontWeight:700, fontSize:14, border:"none", cursor:"pointer", boxShadow:"0 4px 12px rgba(41,171,226,0.3)" }}>进入平台</button>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding:"80px 40px 60px", maxWidth:1200, margin:"0 auto", display:"grid", gridTemplateColumns:"1fr 1fr", gap:60, alignItems:"center" }}>
        <div>
          <div style={{ display:"inline-flex", alignItems:"center", gap:6, background:"#EBF8FF", color:"#29ABE2", padding:"6px 14px", borderRadius:100, fontSize:12, fontWeight:700, marginBottom:20, border:"1px solid #B3E0F5" }}>
            🚀 AI 驱动的下一代招聘平台
          </div>
          <h1 style={{ fontSize:48, fontWeight:800, color:"#1E293B", lineHeight:1.2, marginBottom:20 }}>
            开口即结果<br />
            <span style={{ background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>交付即匹配</span>
          </h1>
          <p style={{ fontSize:17, color:"#64748B", lineHeight:1.7, marginBottom:32 }}>
            以语音交互为入口，AI Agent 为中枢，大模型为生成能力。<br />
            告别筛选简历，告别虚假信息，用技术重构招聘价值。
          </p>
          <div style={{ display:"flex", gap:12 }}>
            <button onClick={() => navigate("/dashboard")} style={{ padding:"14px 28px", borderRadius:12, background:"linear-gradient(135deg,#29ABE2,#1A8FBF)", color:"white", fontWeight:700, fontSize:15, border:"none", cursor:"pointer", boxShadow:"0 6px 20px rgba(41,171,226,0.35)" }}>
              免费开始使用 →
            </button>
            <button style={{ padding:"14px 28px", borderRadius:12, background:"white", color:"#29ABE2", fontWeight:700, fontSize:15, border:"1.5px solid #B3E0F5", cursor:"pointer" }}>
              查看演示
            </button>
          </div>
          <div style={{ display:"flex", gap:24, marginTop:28 }}>
            {[{v:"10,000+",l:"企业用户"},{v:"500K+",l:"候选人"},{v:"87%",l:"匹配准确率"}].map(s => (
              <div key={s.l}>
                <p style={{ fontSize:20, fontWeight:800, color:"#1E293B" }}>{s.v}</p>
                <p style={{ fontSize:12, color:"#94A3B8" }}>{s.l}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 语音演示卡片 */}
        <div style={{ background:"white", borderRadius:24, padding:28, boxShadow:"0 20px 60px rgba(0,0,0,0.08)", border:"1px solid #F1F5F9" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:20 }}>
            <div style={{ width:40, height:40, borderRadius:12, background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:20, height:20 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
            </div>
            <div>
              <p style={{ fontSize:15, fontWeight:700, color:"#1E293B" }}>语音发布职位</p>
              <p style={{ fontSize:12, color:"#94A3B8" }}>说出需求，AI 自动生成职位详情</p>
            </div>
          </div>

          <div style={{ background:"#F8FAFC", borderRadius:14, padding:16, marginBottom:16, minHeight:80 }}>
            {demoText ? (
              <p style={{ fontSize:14, color:"#475569", lineHeight:1.7 }}>{demoText}<span style={{ animation:"blink 1s infinite", opacity:recording?1:0 }}>|</span></p>
            ) : (
              <p style={{ fontSize:13, color:"#94A3B8", fontStyle:"italic" }}>点击下方按钮开始语音演示...</p>
            )}
          </div>

          <div style={{ display:"flex", justifyContent:"center", marginBottom:16 }}>
            <button onClick={startDemo} style={{ width:64, height:64, borderRadius:"50%", background:recording?"linear-gradient(135deg,#EF4444,#DC2626)":"linear-gradient(135deg,#29ABE2,#1A8FBF)", border:"none", cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center", boxShadow:recording?"0 8px 24px rgba(239,68,68,0.4)":"0 8px 24px rgba(41,171,226,0.4)" }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:24, height:24 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
            </button>
          </div>

          {demoText && !recording && (
            <div style={{ background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", borderRadius:12, padding:"12px 14px" }}>
              <p style={{ fontSize:12, fontWeight:700, color:"#29ABE2", marginBottom:6 }}>✨ AI 已生成职位画像</p>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {["后端工程师","5年+","Python","Go","分布式系统","35-50K"].map(t => <span key={t} style={{ fontSize:11, fontWeight:600, color:"#1A8FBF", background:"white", padding:"2px 8px", borderRadius:100, border:"1px solid #B3E0F5" }}>{t}</span>)}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 特性 */}
      <section id="features" style={{ padding:"60px 40px", maxWidth:1200, margin:"0 auto" }}>
        <div style={{ textAlign:"center", marginBottom:48 }}>
          <h2 style={{ fontSize:32, fontWeight:800, color:"#1E293B", marginBottom:12 }}>颠覆传统招聘的核心能力</h2>
          <p style={{ fontSize:16, color:"#64748B" }}>从语音到匹配，全流程 AI 自动化</p>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:20 }}>
          {[
            {icon:"🎙️",title:"语音简历生成",desc:"求职者开口即可生成结构化简历，AI 自动提取技能、经历和亮点",color:"#29ABE2",bg:"#EBF8FF"},
            {icon:"🧠",title:"AI 精准匹配",desc:"大模型分析岗位需求与候选人画像，生成匹配度评分和推荐理由",color:"#7C3AED",bg:"#F5F3FF"},
            {icon:"🔍",title:"多源数据核验",desc:"集成学信网、社保等第三方数据源，自动核验学历和工作经历真实性",color:"#059669",bg:"#ECFDF5"},
            {icon:"🗺️",title:"知识图谱可视化",desc:"展示技能、行业、岗位之间的关联关系，发现隐性人才",color:"#D97706",bg:"#FFFBEB"},
            {icon:"💰",title:"成功付费模式",desc:"候选人通过试用期后才触发付款，零风险的招聘成本结构",color:"#E11D48",bg:"#FFF1F2"},
            {icon:"📊",title:"人才洞察报告",desc:"基于平台数据提供行业薪资水平、人才流动趋势等深度分析",color:"#0D9488",bg:"#E8F5F3"},
          ].map((f,i) => (
            <div key={i} style={{ background:"white", borderRadius:16, padding:24, border:"1px solid #F1F5F9", boxShadow:"0 2px 8px rgba(0,0,0,0.04)", transition:"all 0.25s ease" }}>
              <div style={{ width:48, height:48, borderRadius:14, background:f.bg, display:"flex", alignItems:"center", justifyContent:"center", fontSize:22, marginBottom:14 }}>{f.icon}</div>
              <h3 style={{ fontSize:16, fontWeight:700, color:"#1E293B", marginBottom:8 }}>{f.title}</h3>
              <p style={{ fontSize:13, color:"#64748B", lineHeight:1.7 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 定价 */}
      <section id="pricing" style={{ padding:"60px 40px", background:"linear-gradient(160deg,#EBF8FF,#F5F8FF,#E8F5F3)", borderTop:"1px solid #E2E8F0", borderBottom:"1px solid #E2E8F0" }}>
        <div style={{ maxWidth:900, margin:"0 auto" }}>
          <div style={{ textAlign:"center", marginBottom:40 }}>
            <h2 style={{ fontSize:32, fontWeight:800, color:"#1E293B", marginBottom:12 }}>透明定价，按效果付费</h2>
            <p style={{ fontSize:16, color:"#64748B" }}>候选人入职并通过试用期后才收费，零风险</p>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:20 }}>
            {[
              {plan:"基础版",price:"免费",desc:"适合小型企业起步",features:["5 个活跃职位","AI 基础匹配","候选人管理","招聘管道看板"],cta:"免费开始",primary:false},
              {plan:"专业版",price:"¥2,999/月",desc:"适合成长期企业",features:["无限职位","AI 精准匹配","多源数据核验","人才洞察报告","专属客户经理"],cta:"立即升级",primary:true},
              {plan:"成功付费",price:"入职薪资×15%",desc:"适合高端岗位招聘",features:["猎头级服务","全程 AI 辅助","背景调查核验","入职后付费","无效全额退款"],cta:"联系我们",primary:false},
            ].map((p,i) => (
              <div key={i} style={{ background:"white", borderRadius:20, padding:28, border:p.primary?"2px solid #29ABE2":"1px solid #E2E8F0", boxShadow:p.primary?"0 8px 32px rgba(41,171,226,0.15)":"0 2px 8px rgba(0,0,0,0.04)", position:"relative" }}>
                {p.primary && <div style={{ position:"absolute", top:-12, left:"50%", transform:"translateX(-50%)", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", color:"white", fontSize:11, fontWeight:700, padding:"4px 14px", borderRadius:100 }}>最受欢迎</div>}
                <h3 style={{ fontSize:16, fontWeight:700, color:"#1E293B", marginBottom:4 }}>{p.plan}</h3>
                <p style={{ fontSize:13, color:"#64748B", marginBottom:16 }}>{p.desc}</p>
                <p style={{ fontSize:22, fontWeight:800, color:p.primary?"#29ABE2":"#1E293B", marginBottom:20 }}>{p.price}</p>
                <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:24 }}>
                  {p.features.map(f => <div key={f} style={{ display:"flex", alignItems:"center", gap:8, fontSize:13, color:"#475569" }}><span style={{ color:"#059669", fontWeight:700 }}>✓</span>{f}</div>)}
                </div>
                <button onClick={() => navigate("/dashboard")} style={{ width:"100%", padding:"12px", borderRadius:12, background:p.primary?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"white", color:p.primary?"white":"#29ABE2", fontWeight:700, fontSize:14, border:p.primary?"none":"1.5px solid #B3E0F5", cursor:"pointer", boxShadow:p.primary?"0 4px 14px rgba(41,171,226,0.3)":"none" }}>{p.cta}</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding:"32px 40px", background:"white", borderTop:"1px solid #F1F5F9" }}>
        <div style={{ maxWidth:1200, margin:"0 auto", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <div style={{ width:28, height:28, borderRadius:8, background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center" }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:14, height:14 }}><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
            </div>
            <span style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>HigherMatch</span>
          </div>
          <p style={{ fontSize:13, color:"#94A3B8" }}>© 2026 HigherMatch. 用 AI 重构招聘价值。</p>
        </div>
      </footer>
      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`}</style>
    </div>
  );
};

export default LandingPage;
