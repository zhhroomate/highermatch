import React, { useState, useRef, useEffect } from "react";
import { apiClient } from "../api/client";

interface Message { role: "user"|"assistant"; content: string; }

const GREET = "你好！我是 HigherMatch AI 顾问 🤖\n\n我可以帮你：\n• 分析简历优化建议\n• 解答面试技巧\n• 推荐合适岗位\n• 制定职业规划\n\n有什么可以帮到你？";

const AIAdvisorBubble: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Message[]>([{ role:"assistant", content:GREET }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (open) bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [msgs, open]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const newMsgs: Message[] = [...msgs, { role:"user", content:text }];
    setMsgs(newMsgs);
    setLoading(true);
    try {
      const res = await apiClient.post<{ reply: string }>("/ai/chat", { message:text });
      setMsgs(m => [...m, { role:"assistant", content:res.reply || "我正在思考中，请稍候..." }]);
    } catch {
      const replies = ["根据你的经历，建议重点突出项目成果和数据指标，让 HR 快速了解你的价值。","面试技巧方面，STAR 法则（情境-任务-行动-结果）非常有效，建议提前准备 3-5 个典型案例。","你的技术栈非常适合推荐系统方向，字节跳动和阿里巴巴都有高度匹配的岗位。"];
      setMsgs(m => [...m, { role:"assistant", content:replies[Math.floor(Math.random()*replies.length)] }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="ai-bubble">
      {open && (
        <div style={{ position:"absolute", bottom:64, right:0, width:320, height:420, background:"white", borderRadius:20, boxShadow:"0 8px 32px rgba(0,0,0,0.12)", border:"1px solid #E2E8F0", display:"flex", flexDirection:"column", overflow:"hidden" }}>
          <div style={{ background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", padding:"14px 16px", display:"flex", alignItems:"center", gap:10 }}>
            <div style={{ width:32, height:32, borderRadius:"50%", background:"rgba(255,255,255,0.2)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16 }}>🤖</div>
            <div style={{ flex:1 }}>
              <p style={{ color:"white", fontWeight:700, fontSize:14 }}>AI 职业顾问</p>
              <p style={{ color:"rgba(255,255,255,0.8)", fontSize:11 }}>随时为你提供求职建议</p>
            </div>
            <button onClick={() => setOpen(false)} style={{ background:"rgba(255,255,255,0.2)", border:"none", borderRadius:8, width:28, height:28, display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", color:"white", fontSize:18, lineHeight:1 }}>×</button>
          </div>
          <div style={{ flex:1, overflowY:"auto", padding:"12px 12px 0" }}>
            {msgs.map((m,i) => (
              <div key={i} style={{ display:"flex", justifyContent:m.role==="user"?"flex-end":"flex-start", marginBottom:10 }}>
                {m.role === "assistant" && <div style={{ width:28, height:28, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:12, marginRight:6, flexShrink:0, alignSelf:"flex-end" }}>🤖</div>}
                <div className={m.role==="user"?"msg-user":"msg-ai"} style={{ whiteSpace:"pre-line" }}>{m.content}</div>
              </div>
            ))}
            {loading && (
              <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:10 }}>
                <div style={{ width:28, height:28, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:12 }}>🤖</div>
                <div className="msg-ai" style={{ display:"flex", gap:4, alignItems:"center" }}>
                  {[0,1,2].map(i => <div key={i} style={{ width:6, height:6, borderRadius:"50%", background:"#29ABE2", animation:`bounce 1s ease-in-out ${i*0.15}s infinite` }} />)}
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <div style={{ padding:"10px 12px", borderTop:"1px solid #F1F5F9", display:"flex", gap:8 }}>
            <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key==="Enter" && send()} placeholder="输入问题..." className="input" style={{ flex:1, padding:"8px 12px", fontSize:13, borderRadius:10 }} />
            <button onClick={send} disabled={!input.trim()||loading} style={{ width:36, height:36, borderRadius:10, background:input.trim()?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F1F5F9", border:"none", cursor:input.trim()?"pointer":"default", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
              <svg viewBox="0 0 24 24" fill="none" stroke={input.trim()?"white":"#94A3B8"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22,2 15,22 11,13 2,9 22,2"/></svg>
            </button>
          </div>
        </div>
      )}
      <button className="ai-bubble-btn" onClick={() => setOpen(!open)}>
        {open ? <span style={{ color:"white", fontSize:20, fontWeight:700 }}>×</span> : <span style={{ fontSize:22 }}>🤖</span>}
      </button>
      <style>{`@keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }`}</style>
    </div>
  );
};

export default AIAdvisorBubble;
