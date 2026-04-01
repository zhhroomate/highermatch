import React, { useState, useRef, useEffect } from "react";

interface KGNode {
  id: string; label: string; type: "skill" | "job" | "industry" | "person";
  x: number; y: number; size: number; color: string;
}
interface KGEdge { from: string; to: string; weight: number; }

const NODES: KGNode[] = [
  // 核心技能
  { id:"python", label:"Python", type:"skill", x:200, y:200, size:28, color:"#29ABE2" },
  { id:"go", label:"Go", type:"skill", x:320, y:160, size:22, color:"#29ABE2" },
  { id:"ml", label:"机器学习", type:"skill", x:140, y:300, size:26, color:"#7C3AED" },
  { id:"spark", label:"Spark", type:"skill", x:80, y:200, size:18, color:"#29ABE2" },
  { id:"kafka", label:"Kafka", type:"skill", x:300, y:280, size:18, color:"#29ABE2" },
  { id:"redis", label:"Redis", type:"skill", x:380, y:240, size:16, color:"#29ABE2" },
  // 岗位
  { id:"backend", label:"后端工程师", type:"job", x:240, y:100, size:30, color:"#059669" },
  { id:"algo", label:"算法工程师", type:"job", x:100, y:120, size:26, color:"#059669" },
  { id:"data", label:"数据工程师", type:"job", x:360, y:340, size:22, color:"#059669" },
  // 行业
  { id:"tech", label:"互联网", type:"industry", x:200, y:380, size:32, color:"#D97706" },
  { id:"finance", label:"金融科技", type:"industry", x:360, y:100, size:24, color:"#D97706" },
  // 人才
  { id:"user", label:"张明", type:"person", x:200, y:200, size:20, color:"#E11D48" },
];

const EDGES: KGEdge[] = [
  { from:"python", to:"backend", weight:0.9 },
  { from:"python", to:"algo", weight:0.85 },
  { from:"python", to:"ml", weight:0.95 },
  { from:"go", to:"backend", weight:0.8 },
  { from:"ml", to:"algo", weight:0.9 },
  { from:"spark", to:"data", weight:0.85 },
  { from:"kafka", to:"backend", weight:0.7 },
  { from:"kafka", to:"data", weight:0.75 },
  { from:"redis", to:"backend", weight:0.65 },
  { from:"backend", to:"tech", weight:0.9 },
  { from:"algo", to:"tech", weight:0.85 },
  { from:"data", to:"tech", weight:0.8 },
  { from:"backend", to:"finance", weight:0.6 },
];

const TYPE_CONFIG = {
  skill:    { label:"技能", color:"#29ABE2", bg:"#EBF8FF" },
  job:      { label:"岗位", color:"#059669", bg:"#ECFDF5" },
  industry: { label:"行业", color:"#D97706", bg:"#FFFBEB" },
  person:   { label:"人才", color:"#E11D48", bg:"#FFF1F2" },
};

const KnowledgeGraph: React.FC = () => {
  const [selected, setSelected] = useState<KGNode|null>(null);
  const [filter, setFilter] = useState<"all"|"skill"|"job"|"industry">("all");
  const svgRef = useRef<SVGSVGElement>(null);

  const visibleNodes = NODES.filter(n => filter === "all" || n.type === filter || n.type === "person");
  const visibleIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = EDGES.filter(e => visibleIds.has(e.from) && visibleIds.has(e.to));

  const getRelated = (nodeId: string) => {
    const related = new Set<string>();
    EDGES.forEach(e => {
      if (e.from === nodeId) related.add(e.to);
      if (e.to === nodeId) related.add(e.from);
    });
    return related;
  };

  const related = selected ? getRelated(selected.id) : new Set<string>();

  return (
    <div className="page-container">
      <div className="top-nav">
        <h1 style={{ fontSize:18, fontWeight:800, color:"#1E293B", flex:1 }}>技能知识图谱</h1>
        <span style={{ fontSize:12, color:"#94A3B8", background:"#F8FAFC", padding:"4px 10px", borderRadius:100 }}>AI 分析</span>
      </div>

      <div style={{ padding:"12px 16px 0" }}>
        {/* 说明 */}
        <div style={{ background:"linear-gradient(135deg,#EBF8FF,#E8F5F3)", borderRadius:14, padding:"12px 14px", marginBottom:12, border:"1px solid #B3E0F5" }}>
          <p style={{ fontSize:13, fontWeight:700, color:"#1E293B", marginBottom:4 }}>💡 智能图谱分析</p>
          <p style={{ fontSize:12, color:"#64748B", lineHeight:1.6 }}>基于你的技能档案，AI 构建了技能-岗位-行业关联图谱，发现最适合你的职业路径</p>
        </div>

        {/* 图例 + 筛选 */}
        <div style={{ display:"flex", gap:8, marginBottom:12, overflowX:"auto", scrollbarWidth:"none" }}>
          {[{key:"all",label:"全部"},{key:"skill",label:"技能"},{key:"job",label:"岗位"},{key:"industry",label:"行业"}].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key as any)} style={{ padding:"5px 12px", borderRadius:100, fontSize:12, fontWeight:600, cursor:"pointer", border:"none", whiteSpace:"nowrap", background:filter===f.key?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F8FAFC", color:filter===f.key?"white":"#64748B", boxShadow:filter===f.key?"0 2px 8px rgba(41,171,226,0.3)":"none" }}>{f.label}</button>
          ))}
        </div>

        {/* SVG 图谱 */}
        <div style={{ background:"white", borderRadius:16, border:"1px solid #F1F5F9", overflow:"hidden", marginBottom:12 }}>
          <svg ref={svgRef} viewBox="0 0 460 420" style={{ width:"100%", height:280 }}>
            <defs>
              <radialGradient id="bgGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#F0F7FF" />
                <stop offset="100%" stopColor="#F5F8FF" />
              </radialGradient>
            </defs>
            <rect width="460" height="420" fill="url(#bgGrad)" />

            {/* 边 */}
            {visibleEdges.map((edge, i) => {
              const from = visibleNodes.find(n => n.id === edge.from);
              const to = visibleNodes.find(n => n.id === edge.to);
              if (!from || !to) return null;
              const isHighlighted = selected && (selected.id === edge.from || selected.id === edge.to);
              return (
                <line key={i}
                  x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                  stroke={isHighlighted ? "#29ABE2" : "#E2E8F0"}
                  strokeWidth={isHighlighted ? 2 : 1}
                  strokeOpacity={isHighlighted ? 0.8 : 0.5}
                  strokeDasharray={isHighlighted ? "none" : "4,3"}
                />
              );
            })}

            {/* 节点 */}
            {visibleNodes.map(node => {
              const isSelected = selected?.id === node.id;
              const isRelated = related.has(node.id);
              const isDimmed = selected && !isSelected && !isRelated;
              const cfg = TYPE_CONFIG[node.type];
              return (
                <g key={node.id} className="kg-node" onClick={() => setSelected(isSelected ? null : node)}
                  opacity={isDimmed ? 0.25 : 1}>
                  {isSelected && (
                    <circle cx={node.x} cy={node.y} r={node.size + 8} fill={node.color} opacity={0.15} />
                  )}
                  <circle cx={node.x} cy={node.y} r={node.size}
                    fill={isSelected ? node.color : "white"}
                    stroke={node.color}
                    strokeWidth={isSelected ? 0 : 2}
                    filter={isSelected ? "drop-shadow(0 4px 8px rgba(0,0,0,0.15))" : undefined}
                  />
                  <text x={node.x} y={node.y + 1}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={node.size > 24 ? 10 : 9}
                    fontWeight="700"
                    fill={isSelected ? "white" : node.color}
                  >{node.label}</text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* 选中节点详情 */}
        {selected ? (
          <div className="card fade-in" style={{ padding:16, marginBottom:12 }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
              <div>
                <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:4 }}>
                  <h3 style={{ fontSize:16, fontWeight:800, color:"#1E293B" }}>{selected.label}</h3>
                  <span style={{ fontSize:11, fontWeight:700, color:TYPE_CONFIG[selected.type].color, background:TYPE_CONFIG[selected.type].bg, padding:"2px 8px", borderRadius:100 }}>{TYPE_CONFIG[selected.type].label}</span>
                </div>
                <p style={{ fontSize:12, color:"#64748B" }}>关联节点 {related.size} 个</p>
              </div>
              <button onClick={() => setSelected(null)} style={{ background:"none", border:"none", cursor:"pointer", color:"#94A3B8", fontSize:18 }}>×</button>
            </div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {Array.from(related).map(rid => {
                const rn = NODES.find(n => n.id === rid);
                if (!rn) return null;
                const rc = TYPE_CONFIG[rn.type];
                return <span key={rid} style={{ fontSize:12, fontWeight:600, color:rc.color, background:rc.bg, padding:"3px 10px", borderRadius:100, border:`1px solid ${rc.color}33` }}>{rn.label}</span>;
              })}
            </div>
            {selected.type === "skill" && (
              <div style={{ marginTop:12, background:"#F8FAFC", borderRadius:10, padding:"10px 12px" }}>
                <p style={{ fontSize:12, fontWeight:700, color:"#1E293B", marginBottom:6 }}>市场需求分析</p>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                  <span style={{ fontSize:12, color:"#64748B" }}>需求热度</span>
                  <span style={{ fontSize:12, fontWeight:700, color:"#059669" }}>高</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width:"82%" }} />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:10, marginBottom:12 }}>
            {Object.entries(TYPE_CONFIG).filter(([k]) => k !== "person").map(([type, cfg]) => {
              const count = NODES.filter(n => n.type === type).length;
              return (
                <div key={type} style={{ background:cfg.bg, borderRadius:12, padding:"12px 14px", border:`1px solid ${cfg.color}22` }}>
                  <p style={{ fontSize:18, fontWeight:800, color:cfg.color, marginBottom:2 }}>{count}</p>
                  <p style={{ fontSize:12, color:"#64748B", fontWeight:600 }}>{cfg.label}节点</p>
                </div>
              );
            })}
          </div>
        )}

        {/* 核验状态 */}
        <div className="card" style={{ padding:16 }}>
          <h3 style={{ fontSize:14, fontWeight:700, color:"#1E293B", marginBottom:12 }}>多源数据核验状态</h3>
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {[
              {icon:"🎓",label:"学历核验",sub:"北京大学 · 计算机科学",status:"ok"},
              {icon:"💼",label:"工作经历",sub:"前公司 · 3年任职记录",status:"ok"},
              {icon:"🔒",label:"社保记录",sub:"连续缴纳 60 个月",status:"ok"},
              {icon:"📜",label:"职业资质",sub:"PMP 证书核验中",status:"pending"},
            ].map((item,i) => (
              <div key={i} style={{ display:"flex", alignItems:"center", gap:12, padding:"8px 0", borderBottom:i<3?"1px solid #F1F5F9":"none" }}>
                <div style={{ width:36, height:36, borderRadius:10, background:"#F8FAFC", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, flexShrink:0 }}>{item.icon}</div>
                <div style={{ flex:1 }}>
                  <p style={{ fontSize:13, fontWeight:700, color:"#1E293B", marginBottom:1 }}>{item.label}</p>
                  <p style={{ fontSize:11, color:"#94A3B8" }}>{item.sub}</p>
                </div>
                {item.status === "ok" ? (
                  <span className="verify-badge-ok">✓ 已核验</span>
                ) : (
                  <span className="verify-badge-pending">⏳ 核验中</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeGraph;
