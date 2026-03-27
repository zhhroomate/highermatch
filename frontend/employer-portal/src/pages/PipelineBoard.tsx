/**
 * HigherMatch™ Employer Portal - 候选人管道看板
 * ============================================
 * 拖拽式候选人管道管理
 * 支持实时更新和乐观更新
 *
 * 版本: 1.0.0
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { Card, Typography, Space, Badge, Spin, message, Empty, Tag, Button, Tooltip } from 'antd';
import {
  RobotOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  GiftOutlined,
  UserAddOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import CandidateCard, { Candidate } from '../components/CandidateCard';
import { apiClient } from '../api/client';
import { io, Socket } from 'socket.io-client';

const { Title, Text } = Typography;

/**
 * 管道阶段配置
 */
interface StageConfig {
  id: string;
  title: string;
  icon: React.ReactNode;
  color: string;
  count: number;
}

const STAGES: StageConfig[] = [
  { id: 'ai_recommend', title: 'AI推荐', icon: <RobotOutlined />, color: '#1890ff', count: 0 },
  { id: 'invited', title: '已邀约', icon: <CalendarOutlined />, color: '#722ed1', count: 0 },
  { id: 'interviewing', title: '面试中', icon: <CheckCircleOutlined />, color: '#faad14', count: 0 },
  { id: 'offer', title: 'Offer中', icon: <GiftOutlined />, color: '#f5222d', count: 0 },
  { id: 'hired', title: '入职确认', icon: <UserAddOutlined />, color: '#52c41a', count: 0 },
];

/**
 * Mock 数据
 */
const generateMockCandidates = (): Record<string, Candidate[]> => {
  const candidates: Candidate[] = [
    {
      id: 'c1',
      name: '张明',
      avatar: 'https://i.pravatar.cc/150?img=1',
      city: '北京',
      experienceYears: 5,
      matchScore: 92,
      stage: 'ai_recommend',
      skills: ['Python', 'Go', 'PostgreSQL'],
      lastUpdated: '2小时前',
    },
    {
      id: 'c2',
      name: '李华',
      avatar: 'https://i.pravatar.cc/150?img=2',
      city: '上海',
      experienceYears: 3,
      matchScore: 85,
      stage: 'ai_recommend',
      skills: ['React', 'Vue', 'TypeScript'],
      lastUpdated: '3小时前',
    },
    {
      id: 'c3',
      name: '王芳',
      avatar: 'https://i.pravatar.cc/150?img=3',
      city: '深圳',
      experienceYears: 7,
      matchScore: 78,
      stage: 'ai_recommend',
      skills: ['Java', 'Spring Boot', 'K8s'],
      lastUpdated: '5小时前',
    },
    {
      id: 'c4',
      name: '赵伟',
      avatar: 'https://i.pravatar.cc/150?img=4',
      city: '杭州',
      experienceYears: 4,
      matchScore: 65,
      stage: 'invited',
      skills: ['Python', 'ML', 'TensorFlow'],
      lastUpdated: '1天前',
    },
    {
      id: 'c5',
      name: '刘洋',
      avatar: 'https://i.pravatar.cc/150?img=5',
      city: '广州',
      experienceYears: 6,
      matchScore: 88,
      stage: 'invited',
      skills: ['C++', 'Rust', '系统设计'],
      lastUpdated: '2天前',
    },
    {
      id: 'c6',
      name: '陈静',
      avatar: 'https://i.pravatar.cc/150?img=6',
      city: '成都',
      experienceYears: 2,
      matchScore: 72,
      stage: 'interviewing',
      skills: ['Python', 'Django', 'MySQL'],
      lastUpdated: '3天前',
    },
    {
      id: 'c7',
      name: '杨涛',
      avatar: 'https://i.pravatar.cc/150?img=7',
      city: '北京',
      experienceYears: 8,
      matchScore: 95,
      stage: 'interviewing',
      skills: ['Java', '架构', '微服务'],
      lastUpdated: '1天前',
    },
    {
      id: 'c8',
      name: '周敏',
      avatar: 'https://i.pravatar.cc/150?img=8',
      city: '上海',
      experienceYears: 5,
      matchScore: 82,
      stage: 'offer',
      skills: ['Go', 'K8s', 'DevOps'],
      lastUpdated: '今天',
    },
    {
      id: 'c9',
      name: '吴强',
      avatar: 'https://i.pravatar.cc/150?img=9',
      city: '深圳',
      experienceYears: 4,
      matchScore: 90,
      stage: 'hired',
      skills: ['Python', 'FastAPI', 'Redis'],
      lastUpdated: '已入职',
    },
  ];

  // 按阶段分组
  const grouped: Record<string, Candidate[]> = {
    ai_recommend: [],
    invited: [],
    interviewing: [],
    offer: [],
    hired: [],
  };

  candidates.forEach((c) => {
    grouped[c.stage].push(c);
  });

  return grouped;
};

/**
 * 管道看板组件
 */
interface PipelineBoardProps {
  jobId: string;
  jobTitle?: string;
}

const PipelineBoard: React.FC<PipelineBoardProps> = ({ jobId, jobTitle }) => {
  // 状态
  const [candidatesByStage, setCandidatesByStage] = useState<Record<string, Candidate[]>>({});
  const [flashingCards, setFlashingCards] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Refs
  const socketRef = useRef<Socket | null>(null);
  const previousStateRef = useRef<Record<string, Candidate[]>>({});

  // 计算每个阶段的数量
  const stageCounts = STAGES.reduce((acc, stage) => {
    acc[stage.id] = candidatesByStage[stage.id]?.length || 0;
    return acc;
  }, {} as Record<string, number>);

  // 初始化数据
  const loadCandidates = useCallback(async () => {
    setIsLoading(true);
    try {
      // TODO: 替换为实际 API 调用
      // const response = await apiClient.get(`/api/v1/pipeline/${jobId}`);
      // setCandidatesByStage(response.data);

      // 使用 Mock 数据
      const mockData = generateMockCandidates();
      setCandidatesByStage(mockData);
    } catch (error) {
      console.error('加载候选人失败:', error);
      message.error('加载候选人数据失败');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  // 连接 WebSocket
  const connectWebSocket = useCallback(() => {
    const socketUrl =
      import.meta.env.VITE_WS_URL ||
      (typeof window !== 'undefined' ? window.location.origin : '');

    const socket = io(socketUrl, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      message.success('实时同步已连接');

      // 加入房间
      socket.emit('join', { room: `job_${jobId}` });
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      message.warning('实时同步已断开');
    });

    // 监听管道更新
    socket.on('pipeline.updated', (data: { candidateId: string; newStage: string; updatedBy: string }) => {
      console.log('Received pipeline update:', data);

      // 触发闪烁效果
      setFlashingCards((prev) => new Set([...prev, data.candidateId]));

      // 3秒后移除闪烁
      setTimeout(() => {
        setFlashingCards((prev) => {
          const next = new Set(prev);
          next.delete(data.candidateId);
          return next;
        });
      }, 3000);

      // 更新候选人阶段
      setCandidatesByStage((prev) => {
        const newState = { ...prev };

        // 从原阶段移除
        for (const stage of STAGES) {
          const idx = newState[stage.id]?.findIndex((c) => c.id === data.candidateId);
          if (idx !== undefined && idx > -1) {
            const [candidate] = newState[stage.id].splice(idx, 1);
            // 添加到新阶段
            newState[data.newStage] = [...(newState[data.newStage] || []), {
              ...candidate,
              stage: data.newStage,
            }];
            break;
          }
        }

        return newState;
      });
    });

    socketRef.current = socket;
  }, [jobId]);

  // 移动候选人（乐观更新 + 回滚）
  const moveCandidate = async (candidateId: string, fromStage: string, toStage: string) => {
    // 保存当前状态（用于回滚）
    previousStateRef.current = candidatesByStage;

    // 乐观更新 UI
    setCandidatesByStage((prev) => {
      const newState = { ...prev };
      const candidateIdx = newState[fromStage]?.findIndex((c) => c.id === candidateId);

      if (candidateIdx !== undefined && candidateIdx > -1) {
        const [candidate] = newState[fromStage].splice(candidateIdx, 1);
        newState[toStage] = [...(newState[toStage] || []), {
          ...candidate,
          stage: toStage,
          lastUpdated: '刚刚',
        }];
      }

      return newState;
    });

    try {
      // 调用 API
      await apiClient.post('/api/v1/pipeline/move', {
        candidateId,
        fromStage,
        toStage,
        jobId,
      });

      message.success('候选人已移动');
    } catch (error) {
      console.error('移动失败:', error);

      // 回滚 UI
      setCandidatesByStage(previousStateRef.current);
      message.error('移动失败，已回滚');
    }
  };

  // 处理拖拽结束
  const handleDragEnd = (result: DropResult) => {
    setIsDragging(false);

    if (!result.destination) {
      return;
    }

    const { draggableId, source, destination } = result;

    // 如果没有移动，返回
    if (
      source.droppableId === destination?.droppableId &&
      source.index === destination?.index
    ) {
      return;
    }

    // 执行移动
    moveCandidate(
      draggableId,
      source.droppableId,
      destination!.droppableId
    );
  };

  // 处理拖拽开始
  const handleDragStart = () => {
    setIsDragging(true);
  };

  // 候选人点击
  const handleCandidateClick = (candidate: Candidate) => {
    console.log('Clicked candidate:', candidate);
    // TODO: 打开候选人详情 Modal
    message.info(`查看 ${candidate.name} 的详细信息`);
  };

  // 刷新数据
  const handleRefresh = () => {
    loadCandidates();
    message.info('正在刷新...');
  };

  // 初始化
  useEffect(() => {
    loadCandidates();
    // connectWebSocket(); // 暂时注释，实际使用时启用

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [loadCandidates]);

  // 渲染阶段列
  const renderStageColumn = (stage: StageConfig) => {
    const candidates = candidatesByStage[stage.id] || [];

    return (
      <div
        key={stage.id}
        style={{
          minWidth: 280,
          maxWidth: 320,
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* 列头 */}
        <div
          style={{
            padding: '12px 16px',
            background: '#fafafa',
            borderRadius: '8px 8px 0 0',
            borderBottom: `3px solid ${stage.color}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              <span style={{ color: stage.color }}>{stage.icon}</span>
              <Text strong>{stage.title}</Text>
            </Space>
            <Badge
              count={stageCounts[stage.id]}
              style={{
                backgroundColor: stage.color,
              }}
            />
          </div>
        </div>

        {/* 卡片列表 */}
        <Droppable droppableId={stage.id}>
          {(provided, snapshot) => (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              style={{
                flex: 1,
                padding: 8,
                minHeight: 400,
                background: snapshot.isDraggingOver ? '#e6f7ff' : '#fff',
                borderRadius: '0 0 8px 8px',
                border: '1px solid #f0f0f0',
                borderTop: 'none',
                transition: 'background-color 0.2s ease',
                overflowY: 'auto',
                maxHeight: 'calc(100vh - 300px)',
              }}
            >
              {candidates.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={`暂无${stage.title}候选人`}
                  style={{
                    padding: '40px 0',
                    opacity: 0.6,
                  }}
                />
              ) : (
                candidates.map((candidate, index) => (
                  <Draggable
                    key={candidate.id}
                    draggableId={candidate.id}
                    index={index}
                  >
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.draggableProps}
                        {...provided.dragHandleProps}
                        style={{
                          ...provided.draggableProps.style,
                          marginBottom: 8,
                        }}
                      >
                        <CandidateCard
                          candidate={candidate}
                          isDragging={snapshot.isDragging}
                          isFlashing={flashingCards.has(candidate.id)}
                          onClick={handleCandidateClick}
                        />
                      </div>
                    )}
                  </Draggable>
                ))
              )}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </div>
    );
  };

  if (isLoading) {
    return (
      <Card>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: 400,
          }}
        >
          <Spin size="large" tip="加载候选人数据..." />
        </div>
      </Card>
    );
  }

  return (
    <div className="pipeline-board">
      {/* 头部 */}
      <Card
        style={{ marginBottom: 16 }}
        styles={{ body: { padding: '12px 24px' } }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              候选人管道
            </Title>
            {jobTitle && (
              <Tag color="blue">{jobTitle}</Tag>
            )}
            <Tag>职位ID: {jobId}</Tag>
          </Space>

          <Space>
            {/* 连接状态 */}
            <Tooltip title={isConnected ? '实时同步已连接' : '实时同步未连接'}>
              <Badge status={isConnected ? 'success' : 'error'} text="实时同步" />
            </Tooltip>

            {/* 刷新按钮 */}
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
            >
              刷新
            </Button>
          </Space>
        </div>
      </Card>

      {/* 看板主体 */}
      <Card
        styles={{ body: { padding: 0 } }}
      >
        <DragDropContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
          <div
            style={{
              display: 'flex',
              gap: 16,
              padding: 16,
              overflowX: 'auto',
            }}
          >
            {STAGES.map(renderStageColumn)}
          </div>
        </DragDropContext>
      </Card>

      {/* 拖拽提示 */}
      {isDragging && (
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            left: '50%',
            transform: 'translateX(-50%)',
            padding: '12px 24px',
            background: 'rgba(0, 0, 0, 0.8)',
            color: '#fff',
            borderRadius: 8,
            fontSize: 14,
            zIndex: 1000,
          }}
        >
          拖拽到目标列即可移动候选人
        </div>
      )}

      <style>{`
        .pipeline-board::-webkit-scrollbar {
          height: 8px;
        }
        .pipeline-board::-webkit-scrollbar-track {
          background: #f0f0f0;
          border-radius: 4px;
        }
        .pipeline-board::-webkit-scrollbar-thumb {
          background: #d9d9d9;
          border-radius: 4px;
        }
        .pipeline-board::-webkit-scrollbar-thumb:hover {
          background: #bfbfbf;
        }
      `}</style>
    </div>
  );
};

export default PipelineBoard;
