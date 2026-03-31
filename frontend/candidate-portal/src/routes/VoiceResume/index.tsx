import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";

type Step = "intro" | "recording" | "processing" | "result";

interface ResumeData {
  name: string; title: string; summary: string;
  skills: string[]; experience: { company: string; role: string; duration: string; desc: string }[];
  education: { school: string; degree: string; year: string };
  matchScore: number;
}

const MOCK_RESUME: ResumeData = {
  name: "张明",
  title: "高级后端工程师",
  summary: "5 年互联网后端开发经验，专注于高并发分布式系统和推荐算法。主导过日均亿级请求的服务架构设计，熟悉 Python、Go 技术栈。",
  skills: ["Python", "Go", "PostgreSQL", "Redis", "Kafka", "微服务", "推荐系统", "Docker", "Kubernetes"],
  experience: [
    { company:"字节跳动", role:"高级后端工程师", duration:"2022.03 - 至今", desc:"负责推荐系统后端架构，优化召回和排序模块，日均处理 5 亿次请求" },
    { company:"阿里巴巴", role:"后端工程师", duration:"2019.07 - 2022.02", desc:"参与电商搜索系统开发，负责商品索引和实时更新服务" },
  ],
  education: { school:"北京大学", degree:"计算机科学与技术 · 本科", year:"2019" },
  matchScore: 96,
};

const VoiceResume: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("intro");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [progress, setProgress] = useState(0);
  const [resume, setResume] = useState<ResumeData|null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>|null>(null);
  const waveHeights = [0.4, 0.7, 1.0, 0.6, 0.9, 0.5, 0.8, 0.4, 0.7, 0.6, 0.9, 0.5];

  const startRecording = () => {
    setRecording(true);
    setStep("recording");
    setSeconds(0);
    timerRef.current = setInterval(() => setSeconds(s => s + 1), 1000);
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setRecording(false);
    setStep("processing");
    let p = 0;
    const interval = setInterval(() => {
      p += Math.random() * 15 + 5;
      if (p >= 100) {
        p = 100;
        clearInterval(interval);
        setTimeout(() => { setResume(MOCK_RESUME); setStep("result"); }, 300);
      }
      setProgress(Math.min(p, 100));
    }, 200);
  };

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const fmt = (s: number) => `${Math.floor(s/60).toString().padStart(2,"0")}:${(s%60).toString().padStart(2,"0")}`;

  return (
    <div className="page-container">
      <div className="top-nav">
        <button onClick={() => navigate(-1)} style={{ background:"none", border:"none", cursor:"pointer", padding:4, display:"flex" }}>
          <svg viewBox="0 0 24 24" fill="none" stroke="#64748B" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:20, height:20 }}><polyline points="15,18 9,12 15,6"/></svg>
        </button>
        <h1 style={{ fontSize:17, fontWeight:800, color:"#1E293B", flex:1 }}>语音简历生成</h1>
        {step === "result" && <button onClick={() => setStep("intro")} style={{ fontSize:12, color:"#29ABE2", fontWeight:700, background:"none", border:"none", cursor:"pointer" }}>重录</button>}
      </div>

      <div style={{ padding:"20px 16px" }}>
        {/* 介绍步骤 */}
        {step === "intro" && (
          <div className="fade-in">
            <div style={{ background:"linear-gradient(160deg,#EBF8FF 0%,#F0F7FF 60%,#E8F5F3 100%)", borderRadius:20, padding:24, marginBottom:20, textAlign:"center" }}>
              <div style={{ width:72, height:72, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 16px", boxShadow:"0 8px 24px rgba(41,171,226,0.3)" }}>
                <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:32, height:32 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
              </div>
              <h2 style={{ fontSize:20, fontWeight:800, color:"#1E293B", marginBottom:8 }}>开口即简历</h2>
              <p style={{ fontSize:14, color:"#64748B", lineHeight:1.7 }}>只需用语音描述你的工作经历和技能，AI 将自动生成结构化简历，无需填写任何表单</p>
            </div>

            <div style={{ display:"flex", flexDirection:"column", gap:12, marginBottom:24 }}>
              {[
                {step:"1",title:"开始录音",desc:"点击下方麦克风按钮，用自然语言描述你的经历"},
                {step:"2",title:"AI 分析",desc:"Whisper AI 转录语音，大模型提取关键信息"},
                {step:"3",title:"生成简历",desc:"自动生成结构化简历，支持一键优化和导出"},
              ].map(s => (
                <div key={s.step} style={{ display:"flex", gap:14, alignItems:"flex-start" }}>
                  <div style={{ width:32, height:32, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:13, fontWeight:800, color:"white", flexShrink:0 }}>{s.step}</div>
                  <div>
                    <p style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:2 }}>{s.title}</p>
                    <p style={{ fontSize:13, color:"#64748B", lineHeight:1.5 }}>{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ background:"#FFFBEB", borderRadius:12, padding:"12px 14px", marginBottom:20, border:"1px solid #FDE68A" }}>
              <p style={{ fontSize:12, color:"#D97706", fontWeight:600 }}>💡 提示：可以这样说</p>
              <p style={{ fontSize:12, color:"#64748B", marginTop:4, lineHeight:1.6, fontStyle:"italic" }}>"我叫张明，有 5 年后端开发经验，熟悉 Python 和 Go，在字节跳动做过推荐系统，负责日均亿级请求的架构设计..."</p>
            </div>

            <button className="btn-brand" onClick={startRecording}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:20, height:20 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
              开始语音录入
            </button>
          </div>
        )}

        {/* 录音步骤 */}
        {step === "recording" && (
          <div className="fade-in" style={{ textAlign:"center" }}>
            <div style={{ background:"linear-gradient(160deg,#EBF8FF,#E8F5F3)", borderRadius:20, padding:"32px 24px", marginBottom:20 }}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:4, height:48, marginBottom:20 }}>
                {waveHeights.map((h, i) => (
                  <div key={i} className="wave-bar" style={{ height:`${h * 40}px`, animationDelay:`${i * 0.08}s` }} />
                ))}
              </div>
              <div style={{ width:80, height:80, borderRadius:"50%", background:"linear-gradient(135deg,#EF4444,#DC2626)", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 16px", boxShadow:"0 8px 24px rgba(239,68,68,0.4)", cursor:"pointer" }} onClick={stopRecording}>
                <div style={{ width:24, height:24, borderRadius:4, background:"white" }} />
              </div>
              <p style={{ fontSize:24, fontWeight:800, color:"#1E293B", marginBottom:4 }}>{fmt(seconds)}</p>
              <p style={{ fontSize:13, color:"#64748B" }}>点击停止按钮完成录音</p>
            </div>
            <div style={{ background:"white", borderRadius:14, padding:16, border:"1px solid #F1F5F9" }}>
              <p style={{ fontSize:12, fontWeight:700, color:"#94A3B8", marginBottom:8, textTransform:"uppercase", letterSpacing:"0.05em" }}>AI 实时识别</p>
              <p style={{ fontSize:13, color:"#475569", lineHeight:1.7, textAlign:"left" }}>
                我叫张明，有 5 年后端开发经验，主要用 Python 和 Go...
                <span style={{ animation:"blink 1s infinite", display:"inline-block" }}>|</span>
              </p>
            </div>
            <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}`}</style>
          </div>
        )}

        {/* 处理步骤 */}
        {step === "processing" && (
          <div className="fade-in" style={{ textAlign:"center", padding:"40px 0" }}>
            <div style={{ width:72, height:72, borderRadius:"50%", background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 20px", border:"2px solid #B3E0F5" }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="#29ABE2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width:32, height:32, animation:"spin 2s linear infinite" }}><path d="M21 12a9 9 0 11-6.219-8.56"/></svg>
            </div>
            <h2 style={{ fontSize:18, fontWeight:800, color:"#1E293B", marginBottom:8 }}>AI 正在分析...</h2>
            <p style={{ fontSize:13, color:"#64748B", marginBottom:24 }}>大模型提取关键信息，生成结构化简历</p>
            <div style={{ background:"white", borderRadius:14, padding:20, border:"1px solid #F1F5F9", marginBottom:16 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
                <span style={{ fontSize:13, fontWeight:600, color:"#1E293B" }}>处理进度</span>
                <span style={{ fontSize:13, fontWeight:700, color:"#29ABE2" }}>{Math.round(progress)}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width:`${progress}%` }} />
              </div>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
              {[{label:"语音转文字",done:progress>25},{label:"信息结构化提取",done:progress>55},{label:"技能标签识别",done:progress>75},{label:"简历质量评分",done:progress>90}].map(item => (
                <div key={item.label} style={{ display:"flex", alignItems:"center", gap:10, padding:"8px 14px", background:item.done?"#ECFDF5":"#F8FAFC", borderRadius:10, border:`1px solid ${item.done?"#A7F3D0":"#F1F5F9"}` }}>
                  <span style={{ fontSize:14 }}>{item.done?"✅":"⏳"}</span>
                  <span style={{ fontSize:13, fontWeight:600, color:item.done?"#059669":"#94A3B8" }}>{item.label}</span>
                </div>
              ))}
            </div>
            <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
          </div>
        )}

        {/* 结果步骤 */}
        {step === "result" && resume && (
          <div className="fade-in">
            {/* 匹配分数 */}
            <div style={{ background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", borderRadius:20, padding:20, marginBottom:16, border:"1.5px solid #B3E0F5", textAlign:"center" }}>
              <p style={{ fontSize:13, color:"#64748B", marginBottom:4 }}>✨ 简历生成成功！AI 综合评分</p>
              <p style={{ fontSize:40, fontWeight:800, color:"#059669", lineHeight:1 }}>{resume.matchScore}</p>
              <p style={{ fontSize:12, color:"#64748B", marginTop:4 }}>高于 94% 的求职者</p>
            </div>

            {/* 基本信息 */}
            <div className="card" style={{ padding:16, marginBottom:12 }}>
              <div style={{ display:"flex", gap:14, alignItems:"center" }}>
                <div style={{ width:52, height:52, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:20, fontWeight:800, color:"white", flexShrink:0 }}>{resume.name[0]}</div>
                <div>
                  <h2 style={{ fontSize:17, fontWeight:800, color:"#1E293B", marginBottom:2 }}>{resume.name}</h2>
                  <p style={{ fontSize:13, color:"#64748B", marginBottom:6 }}>{resume.title}</p>
                  <p style={{ fontSize:12, color:"#475569", lineHeight:1.6 }}>{resume.summary}</p>
                </div>
              </div>
            </div>

            {/* 技能 */}
            <div className="card" style={{ padding:16, marginBottom:12 }}>
              <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:10 }}>AI 识别技能</h3>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {resume.skills.map(s => <span key={s} className="tag tag-blue">{s}</span>)}
              </div>
            </div>

            {/* 工作经历 */}
            <div className="card" style={{ padding:16, marginBottom:12 }}>
              <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:12 }}>工作经历</h3>
              {resume.experience.map((exp, i) => (
                <div key={i} style={{ paddingBottom:i<resume.experience.length-1?12:0, marginBottom:i<resume.experience.length-1?12:0, borderBottom:i<resume.experience.length-1?"1px solid #F1F5F9":"none" }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:2 }}>
                    <p style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>{exp.role}</p>
                    <span style={{ fontSize:11, color:"#94A3B8" }}>{exp.duration}</span>
                  </div>
                  <p style={{ fontSize:13, color:"#29ABE2", fontWeight:600, marginBottom:4 }}>{exp.company}</p>
                  <p style={{ fontSize:12, color:"#64748B", lineHeight:1.6 }}>{exp.desc}</p>
                </div>
              ))}
            </div>

            {/* 教育 */}
            <div className="card" style={{ padding:16, marginBottom:16 }}>
              <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:10 }}>教育背景</h3>
              <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                <div style={{ width:40, height:40, borderRadius:10, background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:18 }}>🎓</div>
                <div>
                  <p style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>{resume.education.school}</p>
                  <p style={{ fontSize:12, color:"#64748B" }}>{resume.education.degree} · {resume.education.year}</p>
                </div>
              </div>
            </div>

            <button className="btn-brand" style={{ marginBottom:10 }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
              AI 深度优化简历
            </button>
            <button className="btn-outline">
              <svg viewBox="0 0 24 24" fill="none" stroke="#29ABE2" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7,10 12,15 17,10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              导出 PDF 简历
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VoiceResume;
