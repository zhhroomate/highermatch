import React, { useState } from "react";

export default function VoiceResume() {
  const [recording, setRecording] = useState(false);
  const [hasResume, setHasResume] = useState(false);

  return (
    <div className="hm-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "clamp(22px,3vw,28px)", fontWeight: 800, color: "#0A0A0A", letterSpacing: "-0.03em", marginBottom: 6 }}>语音简历</h1>
        <p style={{ fontSize: 14, color: "#A3A3A3" }}>用语音描述你的经历，AI 自动生成专业简历</p>
      </div>

      {/* 录音区域 */}
      <div className="hm-card-flat" style={{ padding: 32, textAlign: "center", marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
          <button className={`hm-record-btn ${recording ? "recording" : ""}`} onClick={() => { setRecording(!recording); if (recording) setHasResume(true); }}>
            {recording ? (
              <svg viewBox="0 0 24 24" fill="white" style={{ width: 28, height: 28 }}><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 28, height: 28 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
            )}
          </button>
        </div>
        <p style={{ fontSize: 15, fontWeight: 600, color: recording ? "#EF4444" : "#0A0A0A", marginBottom: 6 }}>
          {recording ? "正在录音..." : "点击开始录音"}
        </p>
        <p style={{ fontSize: 13, color: "#A3A3A3" }}>
          {recording ? "再次点击停止，AI 将自动分析你的描述" : "描述你的工作经历、技能和求职意向"}
        </p>
      </div>

      {/* 生成的简历预览 */}
      {hasResume && (
        <div className="hm-card-flat hm-scale-in" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0A0A0A" }}>AI 生成简历</h3>
            <span className="hm-tag hm-tag-success">已生成</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#A3A3A3", marginBottom: 4 }}>基本信息</p>
              <p style={{ fontSize: 14, color: "#404040" }}>5年后端开发经验 · 精通 Go/Python/Java</p>
            </div>
            <hr className="hm-divider" />
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#A3A3A3", marginBottom: 4 }}>核心技能</p>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {["Go", "Python", "微服务", "K8s", "MySQL", "Redis"].map(s => <span key={s} className="hm-tag hm-tag-light">{s}</span>)}
              </div>
            </div>
            <hr className="hm-divider" />
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#A3A3A3", marginBottom: 4 }}>AI 匹配评估</p>
              <p style={{ fontSize: 14, color: "#404040" }}>简历完整度 <strong>92%</strong>，匹配后端工程师岗位 <strong>96 分</strong></p>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
            <button className="hm-btn hm-btn-primary" style={{ flex: 1 }}>导出 PDF</button>
            <button className="hm-btn hm-btn-secondary" style={{ flex: 1 }}>继续优化</button>
          </div>
        </div>
      )}
    </div>
  );
}
