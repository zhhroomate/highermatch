import React from 'react';
import '../index.css';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export default function Dashboard() {
  const funnelData = [
    { stage: '已投递', count: 150, fill: 'var(--hm-info)' },
    { stage: '一面', count: 85, fill: 'var(--hm-warning)' },
    { stage: '二面', count: 45, fill: 'var(--hm-brand)' },
    { stage: '已录用', count: 28, fill: 'var(--hm-success)' },
  ];

  const positionData = [
    { name: '产品经理', value: 35 },
    { name: '设计师', value: 28 },
    { name: '工程师', value: 42 },
    { name: '运营', value: 25 },
  ];

  const COLORS = ['var(--hm-info)', 'var(--hm-warning)', 'var(--hm-brand)', 'var(--hm-success)'];

  return (
    <div className="hm-fade-in" style={{ padding: '32px', background: 'var(--hm-bg)' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 800, marginBottom: '32px' }}>招聘概览</h1>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="hm-card-elevated" style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--hm-gray-500)', marginBottom: '8px' }}>总投递数</p>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: 'var(--hm-info)' }}>328</h2>
        </div>
        <div className="hm-card-elevated" style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--hm-gray-500)', marginBottom: '8px' }}>已录用</p>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: 'var(--hm-success)' }}>28</h2>
        </div>
        <div className="hm-card-elevated" style={{ padding: '24px' }}>
          <p style={{ fontSize: '13px', color: 'var(--hm-gray-500)', marginBottom: '8px' }}>转化率</p>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: 'var(--hm-brand)' }}>8.5%</h2>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div className="hm-card-elevated" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>招聘漏斗</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={funnelData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--hm-gray-100)" />
              <XAxis dataKey="stage" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="var(--hm-info)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="hm-card-elevated" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '16px' }}>岗位分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={positionData} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name} ${value}`} outerRadius={80} fill="#8884d8" dataKey="value">
                {positionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
