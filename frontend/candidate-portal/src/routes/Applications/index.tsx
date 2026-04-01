import React, { useState } from 'react';
import '../../index.css';

export default function Applications() {
  const applications = [
    { id: 1, job: '产品经理', company: '字节跳动', stage: '已投递', progress: 20, date: '2024-03-15' },
    { id: 2, job: '设计师', company: '腾讯', stage: '一面通过', progress: 50, date: '2024-03-10' },
    { id: 3, job: '工程师', company: '阿里', stage: '二面中', progress: 70, date: '2024-03-05' },
    { id: 4, job: '运营', company: '小红书', stage: '已拒', progress: 0, date: '2024-02-28' },
  ];

  const getStageColor = (stage) => {
    if (stage.includes('通过')) return 'success';
    if (stage.includes('中')) return 'warning';
    if (stage.includes('拒')) return 'error';
    return 'info';
  };

  return (
    <div className="hm-fade-in" style={{ paddingBottom: 'var(--hm-bottom-h)' }}>
      <div style={{ padding: '16px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 800, marginBottom: '20px' }}>我的申请</h1>
        
        {applications.map(app => (
          <div key={app.id} className="hm-card" style={{ marginBottom: '12px', padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 700 }}>{app.job}</h3>
                <p style={{ fontSize: '13px', color: 'var(--hm-gray-500)' }}>{app.company} · {app.date}</p>
              </div>
              <span className={`hm-tag hm-tag-${getStageColor(app.stage)}`}>{app.stage}</span>
            </div>
            
            <div className={`hm-progress hm-progress-${getStageColor(app.stage)}`}>
              <div className="hm-progress-fill" style={{ width: app.progress + '%' }}></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
