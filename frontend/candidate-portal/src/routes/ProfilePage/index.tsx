/**
 * HigherMatch™ Candidate Portal - 档案页面
 * ============================================
 * 候选人档案编辑页面
 * 包含模块化折叠面板、进度条、技能标签等
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  NavBar,
  ProgressBar,
  Collapse,
  List,
  Input,
  Button,
  Avatar,
  Space,
  Tag,
  TextArea,
  Slider,
  Selector,
  Switch,
  DatePicker,
  Dialog,
  Toast,
  Popup,
  Image,
} from 'antd-mobile';
import {
  UserOutline,
  EditSFill,
  CameraOutline,
  TextOutline,
  ShopbagOutline,
  SetOutline,
  LocationOutline,
  MailOutline,
  PhoneFill,
  DeleteOutline,
  AddOutline,
  CheckCircleOutline,
  CloseCircleOutline,
  FileOutline,
  UploadOutline,
} from 'antd-mobile-icons';
import { useProfileStore } from '../../stores/profileStore';
import { apiClient } from '../../api/client';
import './index.css';

// ==================== 类型定义 ====================

interface EducationFormData {
  id: string;
  school: string;
  degree: string;
  major: string;
  startDate: string;
  endDate: string;
}

interface WorkFormData {
  id: string;
  company: string;
  position: string;
  description: string;
  startDate: string;
  endDate: string;
}

// ==================== 常量 ====================

const DEGREE_OPTIONS = ['高中', '中专', '大专', '本科', '硕士', '博士'];
const JOB_TYPE_OPTIONS = [
  { label: '全职', value: 'full-time' },
  { label: '兼职', value: 'part-time' },
  { label: '实习', value: 'internship' },
  { label: '外包', value: 'contract' },
];
const CITY_OPTIONS = [
  '北京', '上海', '深圳', '广州', '杭州', '成都', '南京',
  '苏州', '武汉', '西安', '厦门', '长沙', '天津', '重庆',
  '郑州', '东莞', '青岛', '济南', '大连', '沈阳',
];
const SALARY_MARKS = {
  0: '5K',
  25: '15K',
  50: '25K',
  75: '40K',
  100: '60K+',
};

// ==================== 子组件 ====================

/**
 * 头像上传组件
 */
const AvatarUploader: React.FC<{
  value?: string;
  onChange: (url: string) => void;
}> = ({ value, onChange }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      // 模拟上传
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const url = URL.createObjectURL(file);
      onChange(url);
      Toast.show('头像上传成功');
    } catch (error) {
      Toast.show('上传失败');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div className="avatar-uploader">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="camera"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
      <div className="avatar-wrapper" onClick={() => inputRef.current?.click()}>
        {value ? (
          <Image src={value} fit="cover" className="avatar-image" />
        ) : (
          <div className="avatar-placeholder">
            <CameraOutline />
          </div>
        )}
        <div className="avatar-overlay">
          <CameraOutline />
        </div>
      </div>
      {uploading && <div className="uploading-indicator">上传中...</div>}
    </div>
  );
};

/**
 * 教育经历编辑表单
 */
const EducationForm: React.FC<{
  data: EducationFormData;
  onSave: (data: EducationFormData) => void;
  onCancel: () => void;
  onDelete: () => void;
}> = ({ data, onSave, onCancel, onDelete }) => {
  const [formData, setFormData] = useState(data);

  const handleSave = () => {
    if (!formData.school || !formData.degree || !formData.major) {
      Toast.show('请填写必填项');
      return;
    }
    onSave(formData);
  };

  return (
    <div className="form-container">
      <List>
        <List.Item>
          <Input
            placeholder="学校名称"
            value={formData.school}
            onChange={(val) => setFormData({ ...formData, school: val })}
          />
        </List.Item>
        <List.Item>
          <Selector
            options={DEGREE_OPTIONS.map((d) => ({ label: d, value: d }))}
            value={[formData.degree]}
            onChange={(val) => setFormData({ ...formData, degree: val[0] || '' })}
            multiple={false}
          />
        </List.Item>
        <List.Item>
          <Input
            placeholder="专业"
            value={formData.major}
            onChange={(val) => setFormData({ ...formData, major: val })}
          />
        </List.Item>
        <List.Item>
          <Space block direction="vertical">
            <DatePicker
              title="开始时间"
              value={formData.startDate ? new Date(formData.startDate) : undefined}
              onChange={(val) => setFormData({ ...formData, startDate: val?.toISOString().split('T')[0] || '' })}
            >
              <List.Item arrow="horizontal">开始时间</List.Item>
            </DatePicker>
            <DatePicker
              title="结束时间"
              value={formData.endDate ? new Date(formData.endDate) : undefined}
              onChange={(val) => setFormData({ ...formData, endDate: val?.toISOString().split('T')[0] || '' })}
            >
              <List.Item arrow="horizontal">结束时间</List.Item>
            </DatePicker>
          </Space>
        </List.Item>
      </List>
      <div className="form-actions">
        <Button color="danger" size="small" onClick={onDelete}>
          <DeleteOutline /> 删除
        </Button>
        <Space>
          <Button size="small" onClick={onCancel}>
            取消
          </Button>
          <Button color="primary" size="small" onClick={handleSave}>
            <CheckCircleOutline /> 保存
          </Button>
        </Space>
      </div>
    </div>
  );
};

/**
 * 工作经历编辑表单
 */
const WorkForm: React.FC<{
  data: WorkFormData;
  onSave: (data: WorkFormData) => void;
  onCancel: () => void;
  onDelete: () => void;
}> = ({ data, onSave, onCancel, onDelete }) => {
  const [formData, setFormData] = useState(data);

  const handleSave = () => {
    if (!formData.company || !formData.position) {
      Toast.show('请填写必填项');
      return;
    }
    onSave(formData);
  };

  return (
    <div className="form-container">
      <List>
        <List.Item>
          <Input
            placeholder="公司名称"
            value={formData.company}
            onChange={(val) => setFormData({ ...formData, company: val })}
          />
        </List.Item>
        <List.Item>
          <Input
            placeholder="职位"
            value={formData.position}
            onChange={(val) => setFormData({ ...formData, position: val })}
          />
        </List.Item>
        <List.Item>
          <TextArea
            placeholder="工作描述"
            value={formData.description}
            onChange={(val) => setFormData({ ...formData, description: val })}
            rows={4}
          />
        </List.Item>
        <List.Item>
          <Space block direction="vertical">
            <DatePicker
              title="开始时间"
              value={formData.startDate ? new Date(formData.startDate) : undefined}
              onChange={(val) => setFormData({ ...formData, startDate: val?.toISOString().split('T')[0] || '' })}
            >
              <List.Item arrow="horizontal">开始时间</List.Item>
            </DatePicker>
            <DatePicker
              title="结束时间"
              value={formData.endDate ? new Date(formData.endDate) : undefined}
              onChange={(val) => setFormData({ ...formData, endDate: val?.toISOString().split('T')[0] || '' })}
            >
              <List.Item arrow="horizontal">结束时间</List.Item>
            </DatePicker>
          </Space>
        </List.Item>
      </List>
      <div className="form-actions">
        <Button color="danger" size="small" onClick={onDelete}>
          <DeleteOutline /> 删除
        </Button>
        <Space>
          <Button size="small" onClick={onCancel}>
            取消
          </Button>
          <Button color="primary" size="small" onClick={handleSave}>
            <CheckCircleOutline /> 保存
          </Button>
        </Space>
      </div>
    </div>
  );
};

/**
 * PDF 上传弹窗
 */
const ResumeUploadPopup: React.FC<{
  visible: boolean;
  onClose: () => void;
  onParsed: (data: any) => void;
}> = ({ visible, onClose, onParsed }) => {
  const [uploading, setUploading] = useState(false);
  const [parsing, setParsing] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      Toast.show('请上传 PDF 文件');
      return;
    }

    setUploading(true);
    try {
      // 模拟上传
      await new Promise((resolve) => setTimeout(resolve, 1500));

      setParsing(true);
      // 模拟解析
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // 返回模拟解析数据
      const parsedData = {
        name: '张三',
        phone: '13800138000',
        email: 'zhangsan@example.com',
        education: [
          { school: '北京大学', degree: '硕士', major: '计算机科学', startDate: '2018-09', endDate: '2021-06' },
        ],
        workExperience: [
          { company: '字节跳动', position: '高级工程师', startDate: '2021-07', endDate: '至今', description: '负责后端开发' },
        ],
        skills: ['Python', 'Go', 'PostgreSQL', 'Redis', 'Docker', 'K8s'],
      };

      Toast.show('简历解析成功');
      onParsed(parsedData);
      onClose();
    } catch (error) {
      Toast.show('解析失败，请手动填写');
    } finally {
      setUploading(false);
      setParsing(false);
    }
  };

  return (
    <Popup visible={visible} onClose={onClose} showCloseButton>
      <div className="resume-upload-popup">
        <h3>上传简历自动填充</h3>
        <p className="subtitle">支持 PDF 格式，系统将自动解析并填充表单</p>

        <div className="upload-area" onClick={() => fileRef.current?.click()}>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUpload(file);
            }}
          />
          <UploadOutline fontSize={48} color="#999" />
          <p>点击上传 PDF 简历</p>
          <span>或拖拽文件到此处</span>
        </div>

        {uploading && <div className="loading-tip">正在上传...</div>}
        {parsing && <div className="loading-tip">正在智能解析，请稍候...</div>}

        <Button block color="primary" onClick={onClose} style={{ marginTop: 16 }}>
          稍后手动填写
        </Button>
      </div>
    </Popup>
  );
};

// ==================== 主组件 ====================

const ProfilePage: React.FC = () => {
  const {
    profile,
    updateBasicInfo,
    addEducation,
    updateEducation,
    removeEducation,
    addWorkExperience,
    updateWorkExperience,
    removeWorkExperience,
    addSkill,
    removeSkill,
    updatePreference,
    setProfile,
    calculateCompleteness,
  } = useProfileStore();

  const [skillInput, setSkillInput] = useState('');
  const [showResumeUpload, setShowResumeUpload] = useState(!profile.resumeParsed);
  const [activeKey, setActiveKey] = useState<string[]>([]);

  // 计算完整度
  useEffect(() => {
    calculateCompleteness();
  }, [profile]);

  // 处理教育经历保存
  const handleEducationSave = (data: EducationFormData) => {
    updateEducation(data.id, { ...data, isEditing: false });
  };

  // 处理工作经历保存
  const handleWorkSave = (data: WorkFormData) => {
    updateWorkExperience(data.id, { ...data, isEditing: false });
  };

  // 添加技能
  const handleAddSkill = () => {
    if (skillInput.trim()) {
      addSkill(skillInput.trim());
      setSkillInput('');
    }
  };

  // 处理简历解析完成
  const handleResumeParsed = (data: any) => {
    setProfile({
      name: data.name,
      phone: data.phone,
      email: data.email,
      education: data.education.map((e: any, i: number) => ({
        id: `edu_${Date.now()}_${i}`,
        school: e.school,
        degree: e.degree,
        major: e.major,
        startDate: e.startDate,
        endDate: e.endDate,
      })),
      workExperience: data.workExperience.map((w: any, i: number) => ({
        id: `work_${Date.now()}_${i}`,
        company: w.company,
        position: w.position,
        description: w.description,
        startDate: w.startDate,
        endDate: w.endDate,
      })),
      skills: data.skills,
      resumeParsed: true,
    });
    Toast.show('简历信息已填充');
  };

  // 获取进度条颜色
  const getProgressColor = (percent: number) => {
    if (percent >= 80) return '#52c41a';
    if (percent >= 50) return '#faad14';
    return '#ff4d4f';
  };

  return (
    <div className="profile-page">
      <NavBar
        left={<span>HigherMatch</span>}
        right={
          <span onClick={() => Toast.show('保存成功')}>
            <CheckCircleOutline />
          </span>
        }
      >
        我的档案
      </NavBar>

      {/* 完整度进度条 */}
      <div className="completeness-section">
        <div className="completeness-header">
          <span>档案完整度</span>
          <span style={{ color: getProgressColor(profile.profileCompleteness || 0) }}>
            {profile.profileCompleteness || 0}%
          </span>
        </div>
        <ProgressBar
          percent={profile.profileCompleteness || 0}
          color={getProgressColor(profile.profileCompleteness || 0)}
          trackColor="#f0f0f0"
        />
        <p className="completeness-tip">
          {profile.profileCompleteness >= 80
            ? '您的档案已经很完善了'
            : profile.profileCompleteness >= 50
            ? '继续完善，提高曝光机会'
            : '请尽快完善您的档案信息'}
        </p>
      </div>

      {/* PDF 上传引导 */}
      {!profile.resumeParsed && (
        <div className="resume-guide" onClick={() => setShowResumeUpload(true)}>
          <FileOutline fontSize={24} color="#1890ff" />
          <div className="guide-content">
            <span className="guide-title">上传简历自动填充</span>
            <span className="guide-subtitle">节省填写时间，AI 智能解析</span>
          </div>
          <Button size="small" color="primary">
            上传
          </Button>
        </div>
      )}

      {/* 折叠面板 */}
      <Collapse activeKey={activeKey} onChange={setActiveKey}>
        {/* 基础信息 */}
        <Collapse.Panel
          key="basic"
          title={
            <Space>
              <UserOutline />
              基础信息
            </Space>
          }
        >
          <List>
            <List.Item prefix="头像">
              <AvatarUploader
                value={profile.avatar}
                onChange={(url) => updateBasicInfo({ avatar: url })}
              />
            </List.Item>
            <List.Item prefix="姓名">
              <Input
                placeholder="请输入姓名"
                value={profile.name}
                onChange={(val) => updateBasicInfo({ name: val })}
              />
            </List.Item>
            <List.Item prefix="手机">
              <Input
                placeholder="请输入手机号"
                value={profile.phone}
                onChange={(val) => updateBasicInfo({ phone: val })}
              />
            </List.Item>
            <List.Item prefix="邮箱">
              <Input
                placeholder="请输入邮箱"
                value={profile.email}
                onChange={(val) => updateBasicInfo({ email: val })}
              />
            </List.Item>
            <List.Item prefix="所在城市">
              <Input
                placeholder="请输入所在城市"
                value={profile.location}
                onChange={(val) => updateBasicInfo({ location: val })}
              />
            </List.Item>
            <List.Item prefix="当前职位">
              <Input
                placeholder="如：高级后端工程师"
                value={profile.currentTitle}
                onChange={(val) => updateBasicInfo({ currentTitle: val })}
              />
            </List.Item>
            <List.Item prefix="工作年限">
              <Input
                type="number"
                placeholder="请输入工作年限"
                value={profile.workYears?.toString()}
                onChange={(val) => updateBasicInfo({ workYears: parseInt(val) || 0 })}
              />
            </List.Item>
          </List>
        </Collapse.Panel>

        {/* 教育经历 */}
        <Collapse.Panel
          key="education"
          title={
            <Space>
              <TextOutline />
              教育经历
              {profile.education.length > 0 && (
                <Tag color="primary">{profile.education.length}</Tag>
              )}
            </Space>
          }
        >
          {profile.education.map((edu) =>
            edu.isEditing ? (
              <EducationForm
                key={edu.id}
                data={edu as EducationFormData}
                onSave={handleEducationSave}
                onCancel={() => removeEducation(edu.id)}
                onDelete={() => removeEducation(edu.id)}
              />
            ) : (
              <List key={edu.id}>
                <List.Item
                  extra={
                    <Button
                      size="small"
                      onClick={() => updateEducation(edu.id, { isEditing: true })}
                    >
                      编辑
                    </Button>
                  }
                >
                  <div className="education-item">
                    <div className="edu-school">{edu.school || '未填写'}</div>
                    <div className="edu-detail">
                      {edu.degree} · {edu.major}
                    </div>
                    <div className="edu-date">
                      {edu.startDate} - {edu.endDate}
                    </div>
                  </div>
                </List.Item>
              </List>
            )
          )}
          <Button
            block
            color="primary"
            fill="outline"
            onClick={addEducation}
            style={{ marginTop: 12 }}
          >
            <AddOutline /> 添加教育经历
          </Button>
        </Collapse.Panel>

        {/* 工作经历 */}
        <Collapse.Panel
          key="work"
          title={
            <Space>
              <ShopbagOutline />
              工作经历
              {profile.workExperience.length > 0 && (
                <Tag color="primary">{profile.workExperience.length}</Tag>
              )}
            </Space>
          }
        >
          {profile.workExperience.map((work) =>
            work.isEditing ? (
              <WorkForm
                key={work.id}
                data={work as WorkFormData}
                onSave={handleWorkSave}
                onCancel={() => removeWorkExperience(work.id)}
                onDelete={() => removeWorkExperience(work.id)}
              />
            ) : (
              <List key={work.id}>
                <List.Item
                  extra={
                    <Button
                      size="small"
                      onClick={() => updateWorkExperience(work.id, { isEditing: true })}
                    >
                      编辑
                    </Button>
                  }
                >
                  <div className="work-item">
                    <div className="work-company">{work.company || '未填写'}</div>
                    <div className="work-position">{work.position}</div>
                    {work.description && (
                      <div className="work-desc">{work.description}</div>
                    )}
                    <div className="work-date">
                      {work.startDate} - {work.endDate}
                    </div>
                  </div>
                </List.Item>
              </List>
            )
          )}
          <Button
            block
            color="primary"
            fill="outline"
            onClick={addWorkExperience}
            style={{ marginTop: 12 }}
          >
            <AddOutline /> 添加工作经历
          </Button>
        </Collapse.Panel>

        {/* 技能标签 */}
        <Collapse.Panel
          key="skills"
          title={
            <Space>
              <SetOutline />
              技能标签
              {profile.skills.length > 0 && (
                <Tag color="primary">{profile.skills.length}/30</Tag>
              )}
            </Space>
          }
        >
          <div className="skills-section">
            <div className="skill-input-row">
              <Input
                placeholder="输入技能名称，按回车添加"
                value={skillInput}
                onChange={setSkillInput}
                onEnterPress={handleAddSkill}
                maxLength={20}
              />
              <Button color="primary" onClick={handleAddSkill}>
                添加
              </Button>
            </div>
            <div className="skills-tags">
              {profile.skills.map((skill) => (
                <Tag
                  key={skill}
                  closable
                  onClose={() => removeSkill(skill)}
                  color="primary"
                >
                  {skill}
                </Tag>
              ))}
            </div>
            {profile.skills.length === 0 && (
              <p className="empty-tip">暂无技能标签，添加后可提高匹配精准度</p>
            )}
          </div>
        </Collapse.Panel>

        {/* 求职偏好 */}
        <Collapse.Panel
          key="preference"
          title={
            <Space>
              <LocationOutline />
              求职偏好
            </Space>
          }
        >
          <List>
            <List.Item title="薪资范围">
              <Slider
                range
                min={0}
                max={100}
                marks={SALARY_MARKS}
                value={[profile.salaryMin || 0, profile.salaryMax || 100]}
                onChange={([min, max]) => updatePreference({ salaryMin: min, salaryMax: max })}
              />
            </List.Item>
            <List.Item title="期望城市（可多选）">
              <Selector
                options={CITY_OPTIONS.map((c) => ({ label: c, value: c }))}
                value={profile.preferredCities}
                onChange={(val) => updatePreference({ preferredCities: val as string[] })}
                multiple
              />
            </List.Item>
            <List.Item title="工作类型">
              <Selector
                options={JOB_TYPE_OPTIONS}
                value={profile.jobTypes}
                onChange={(val) => updatePreference({ jobTypes: val as string[] })}
                multiple
              />
            </List.Item>
          </List>
        </Collapse.Panel>
      </Collapse>

      {/* PDF 上传弹窗 */}
      <ResumeUploadPopup
        visible={showResumeUpload}
        onClose={() => setShowResumeUpload(false)}
        onParsed={handleResumeParsed}
      />

      {/* 底部安全区 */}
      <div className="safe-area-bottom" />
    </div>
  );
};

export default ProfilePage;
