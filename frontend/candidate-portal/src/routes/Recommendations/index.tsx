import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../../api/client";

interface Job {
  id: string; title: string; company: string; location: string;
  salary: string; matchScore: number; tags: string[]; type: string;
  isNew?: boolean; isFeatured?: boolean; postedAt?: string; reason?: string;
}

const MOCK_JOBS: Job[] = [
  { id:"1", title:"高级后端工程师", company:"字节跳动", location:"北京", salary:"35-50K", matchScore:96, tags:["Python","Go","微服务"], type:"全职", isNew:true, isFeatured:true, postedAt:"2小时前", reason:"与你的 Python 技能高度匹配，且有推荐系统经验" },
  { id:"2", title:"推荐算法工程师", company:"阿里巴巴", location:"杭州", salary:"40-60K", matchScore:91, tags:["机器学习","Python","Spark"], type:"全职", postedAt:"1天前", reason:"岗位要求与你的技术栈高度契合" },
  { id:"3", title:"后端开发工程师", company:"腾讯", location:"深圳", salary:"28-45K", matchScore:87, tags:["Go","PostgreSQL","Redis"], type:"全职", postedAt:"3天前" },
  { id:"4", title:"数据平台工程师", company:"美团", location:"北京", salary:"30-45K", matchScore:83, tags:["Kafka","Flink","Hive"], type:"全职", postedAt:"5天前" },
  { id:"5", title:"技术负责人", company:"滴滴", location:"北京", salary:"50-80K", matchScore:78, tags:["架构设计","团队管理","Go"], type:"全职", postedAt:"1周前" },
];

const ScoreRing: React.FC<{ score: number; size?: number }> = ({ score, size = 44 }) => {
  const r = (size - 6) / 2;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 90 ? "#059669" : score >= 80 ? "#29ABE2" : "#D97706";
  return (
    <div style={{ position:"relative", width:size, height:size, flexShrink:0 }}>
      <svg width={size} height={size} style={{ transform:"rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#F1F5F9" strokeWidth={4} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={`${fill} ${circ-fill}`} strokeLinecap="round" />
      </svg>
      <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", fontSize:10, fontWeight:800, color }}>{score}</div>
    </div>
  );
};

const FeaturedCard: React.FC<{ job: Job }> = ({ job }) => (
  <div style={{ background:"linear-gradient(135deg,#EBF8FF 0%,#E8F5F3 100%)", borderRadius:20, padding:20, border:"1.5px solid #B3E0F5", boxShadow:"0 4px 20px rgba(41,171,226,0.12)", cursor:"pointer", flexShrink:0, width:280, position:"relative", overflow:"hidden" }}>
    <div style={{ position:"absolute", top:-20, right:-20, width:80, height:80, borderRadius:"50%", background:"rgba(41,171,226,0.08)" }} />
    <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:12 }}>
      <div style={{ width:44, height:44, borderRadius:12, background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, fontWeight:800, color:"white" }}>{job.company[0]}</div>
      <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-end", gap:4 }}>
        {job.isNew && <span style={{ fontSize:10, fontWeight:700, color:"#29ABE2", background:"#EBF8FF", padding:"2px 8px", borderRadius:100, border:"1px solid #B3E0F5" }}>NEW</span>}
        <ScoreRing score={job.matchScore} />
      </div>
    </div>
    <h3 style={{ fontSize:16, fontWeight:800, color:"#1E293B", marginBottom:4 }}>{job.title}</h3>
    <p style={{ fontSize:13, color:"#64748B", marginBottom:10 }}>{job.company} · {job.location}</p>
    <p style={{ fontSize:15, fontWeight:800, color:"#059669", marginBottom:12 }}>{job.salary}</p>
    <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:job.reason?12:0 }}>
      {job.tags.slice(0,3).map(t => <span key={t} className="tag tag-blue" style={{ fontSize:11 }}>{t}</span>)}
    </div>
    {job.reason && <div style={{ background:"rgba(255,255,255,0.7)", borderRadius:10, padding:"8px 10px", fontSize:12, color:"#475569", lineHeight:1.5 }}>💡 {job.reason}</div>}
  </div>
);

const JobCard: React.FC<{ job: Job }> = ({ job }) => {
  const [saved, setSaved] = useState(false);
  const sc = job.matchScore >= 90 ? "#059669" : job.matchScore >= 80 ? "#29ABE2" : "#D97706";
  const sb = job.matchScore >= 90 ? "#ECFDF5" : job.matchScore >= 80 ? "#EBF8FF" : "#FFFBEB";
  return (
    <div className="job-card">
      <div style={{ display:"flex", gap:12, alignItems:"flex-start" }}>
        <div style={{ width:44, height:44, borderRadius:12, background:"linear-gradient(135deg,#F0F7FF,#E8F5F3)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, fontWeight:800, color:"#29ABE2", border:"1px solid #E2E8F0", flexShrink:0 }}>{job.company[0]}</div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:2 }}>
            <h3 style={{ fontSize:15, fontWeight:700, color:"#1E293B", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis", maxWidth:"65%" }}>{job.title}</h3>
            <span style={{ fontSize:12, fontWeight:800, color:sc, background:sb, padding:"2px 8px", borderRadius:100, flexShrink:0 }}>{job.matchScore}%</span>
          </div>
          <p style={{ fontSize:13, color:"#64748B", marginBottom:6 }}>{job.company} · {job.location}</p>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <p style={{ fontSize:14, fontWeight:700, color:"#059669" }}>{job.salary}</p>
            <span style={{ fontSize:11, color:"#94A3B8" }}>{job.postedAt}</span>
          </div>
          <div style={{ display:"flex", gap:6, flexWrap:"wrap", marginTop:8 }}>
            {job.tags.slice(0,3).map(t => <span key={t} className="tag tag-blue" style={{ fontSize:11 }}>{t}</span>)}
          </div>
        </div>
        <button onClick={e => { e.stopPropagation(); setSaved(!saved); }} style={{ background:"none", border:"none", cursor:"pointer", padding:4, flexShrink:0 }}>
          <svg viewBox="0 0 24 24" fill={saved?"#29ABE2":"none"} stroke={saved?"#29ABE2":"#CBD5E1"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width:18, height:18 }}><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
        </button>
      </div>
    </div>
  );
};

const Recommendations: React.FC = () => {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all"|"high"|"new">("all");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await apiClient.get<{ items: Job[] }>("/jobs/recommendations");
        setJobs(res.items || MOCK_JOBS);
      } catch { setJobs(MOCK_JOBS); }
      finally { setLoading(false); }
    };
    load();
  }, []);

  const filtered = jobs.filter(j => filter === "high" ? j.matchScore >= 90 : filter === "new" ? j.isNew : true);
  const featured = jobs.filter(j => j.isFeatured || j.matchScore >= 90);

  return (
    <div className="page-container">
      <div style={{ background:"linear-gradient(160deg,#EBF8FF 0%,#F0F7FF 60%,#E8F5F3 100%)", padding:"20px 16px 24px" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:16 }}>
          <div>
            <p style={{ fontSize:13, color:"#64748B", marginBottom:4 }}>早上好 👋</p>
            <h1 style={{ fontSize:22, fontWeight:800, color:"#1E293B", lineHeight:1.3 }}>
              为你找到<br />
              <span style={{ background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>{jobs.length} 个匹配岗位</span>
            </h1>
          </div>
          <div style={{ width:44, height:44, borderRadius:"50%", background:"linear-gradient(135deg,#29ABE2,#4ECDC4)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:16, fontWeight:800, color:"white", boxShadow:"0 4px 14px rgba(41,171,226,0.3)" }}>张</div>
        </div>
        <div style={{ display:"flex", gap:10 }}>
          <button onClick={() => navigate("/voice-resume")} style={{ flex:1, display:"flex", alignItems:"center", justifyContent:"center", gap:6, padding:"10px 14px", borderRadius:12, background:"linear-gradient(135deg,#29ABE2,#1A8FBF)", color:"white", fontWeight:700, fontSize:13, border:"none", cursor:"pointer", boxShadow:"0 4px 12px rgba(41,171,226,0.3)" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M19 10v2a7 7 0 01-14 0v-2"/></svg>
            语音更新简历
          </button>
          <button style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:6, padding:"10px 14px", borderRadius:12, background:"white", color:"#29ABE2", fontWeight:700, fontSize:13, border:"1.5px solid #B3E0F5", cursor:"pointer" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="#29ABE2" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width:16, height:16 }}><polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46 22,3"/></svg>
            筛选
          </button>
        </div>
      </div>

      <div style={{ padding:"0 0 16px" }}>
        {featured.length > 0 && (
          <div>
            <div style={{ padding:"16px 16px 10px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                <div style={{ width:4, height:16, borderRadius:2, background:"linear-gradient(180deg,#29ABE2,#4ECDC4)" }} />
                <span style={{ fontSize:15, fontWeight:800, color:"#1E293B" }}>AI 精选推荐</span>
              </div>
              <span style={{ fontSize:12, color:"#29ABE2", fontWeight:600 }}>查看全部</span>
            </div>
            <div style={{ display:"flex", gap:12, overflowX:"auto", padding:"0 16px 16px", scrollbarWidth:"none" }}>
              {featured.map(j => <FeaturedCard key={j.id} job={j} />)}
            </div>
          </div>
        )}

        <div style={{ display:"flex", gap:8, padding:"0 16px 12px", overflowX:"auto", scrollbarWidth:"none" }}>
          {[{key:"all",label:"全部"},{key:"high",label:"高匹配 90%+"},{key:"new",label:"最新发布"}].map(f => (
            <button key={f.key} onClick={() => setFilter(f.key as any)} style={{ padding:"6px 14px", borderRadius:100, fontSize:12, fontWeight:600, cursor:"pointer", whiteSpace:"nowrap", border:"none", transition:"all 0.2s", background:filter===f.key?"linear-gradient(135deg,#29ABE2,#1A8FBF)":"#F8FAFC", color:filter===f.key?"white":"#64748B", boxShadow:filter===f.key?"0 2px 8px rgba(41,171,226,0.3)":"none" }}>{f.label}</button>
          ))}
        </div>

        <div style={{ padding:"0 16px", display:"flex", flexDirection:"column", gap:10 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:4 }}>
            <span style={{ fontSize:14, fontWeight:700, color:"#1E293B" }}>为你推荐</span>
            <span style={{ fontSize:12, color:"#94A3B8" }}>{filtered.length} 个结果</span>
          </div>
          {loading ? Array.from({length:4}).map((_,i) => (
            <div key={i} style={{ background:"white", borderRadius:16, padding:16, border:"1px solid #F1F5F9" }}>
              <div style={{ display:"flex", gap:12 }}>
                <div className="skeleton" style={{ width:44, height:44, borderRadius:12, flexShrink:0 }} />
                <div style={{ flex:1, display:"flex", flexDirection:"column", gap:8 }}>
                  <div className="skeleton" style={{ height:16, borderRadius:8, width:"60%" }} />
                  <div className="skeleton" style={{ height:12, borderRadius:8, width:"40%" }} />
                  <div className="skeleton" style={{ height:12, borderRadius:8, width:"80%" }} />
                </div>
              </div>
            </div>
          )) : filtered.map((j,i) => (
            <div key={j.id} className="fade-in" style={{ animationDelay:`${i*0.04}s` }}>
              <JobCard job={j} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Recommendations;
