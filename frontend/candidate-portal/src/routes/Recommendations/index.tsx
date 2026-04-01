import React, { useState } from 'react';
import '../../index.css';

export default function Recommendations() {
  const [selectedJob, setSelectedJob] = useState(0);
  
  const jobs = [
    { id: 1, title: '高级产品经理', company: '字节跳动', match: 92, status: '待投递', tags: ['产品', '5年+经验'] },
    { id: 2, title: '设计总监', company: '腾讯', match: 85, status: '已投递', tags: ['设计', '管理'] },
    { id: 3, title: '技术负责人', company: '阿里巴巴', match: 78, status: '面试中', tags: ['技术', '架构'] },
  ];

  return (
    <div className="hm-fade-in" style={{ paddingBottom: 'var(--hm-bottom-h)' }}>
      <div style={{ padding: '16px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 800, marginBottom: '20px' }}>为你推荐</h1>
        
        {jobs.map((job, idx) => (
          <div key={job.id} className="hm-card-interactive" style={{ marginBottom: '16px', padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '4px' }}>{job.title}</h3>
                <p style={{ fontSize: '13px', color: 'var(--hm-gray-500)' }}>{job.company}</p>
              </div>
              <div className="hm-score" style={{ width: '48px', height: '48px', fontSize: '14px', background: 'linear-gradient(135deg, var(--hm-success), var(--hm-info))' }}>
                {job.match}%
              </div>
            </div>
            
            <div style={{ marginBottom: '12px' }}>
              <div className="hm-progress" style={{ marginBottom: '8px' }}>
                <div className="hm-progress-fill" style={{ width: job.match + '%' }}></div>
              </div>
              <span className={`hm-tag hm-tag-${job.status === '待投递' ? 'warning' : job.status === '已投递' ? 'info' : 'success'}`}>
                {job.status}
              </span>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {job.tags.map(tag => (
                <span key={tag} className="hm-tag hm-tag-light" style={{ fontSize: '12px' }}>{tag}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
