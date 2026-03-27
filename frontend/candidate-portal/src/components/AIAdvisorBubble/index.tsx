/**
 * HigherMatch™ Candidate Portal - AI 职业顾问气泡组件
 * ============================================
 * 全局右下角悬浮气泡，支持展开对话和 action_cards
 *
 * 版本: 1.0.0
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Dialog,
  Button,
  Input,
  Toast,
  DotLoading,
} from 'antd-mobile';
import {
  AntOutline,
  SendOutline,
  CloseCircleFill,
  FaceRecognitionOutline,
  UserOutline,
  CheckCircleOutline,
} from 'antd-mobile-icons';
import './index.css';

// ==================== 类型定义 ====================

export interface ActionCard {
  id: string;
  type: 'job' | 'resume' | 'interview';
  title: string;
  description: string;
  actionText: string;
  onAction: () => void;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  actionCards?: ActionCard[];
  timestamp: Date;
}

// ==================== 组件 ====================

/**
 * 打字机动画组件
 */
const TypingIndicator: React.FC = () => {
  return (
    <div className="typing-indicator">
      <span className="dot"></span>
      <span className="dot"></span>
      <span className="dot"></span>
    </div>
  );
};

/**
 * Action Card 组件
 */
const ActionCard: React.FC<{
  card: ActionCard;
}> = ({ card }) => {
  const handleClick = () => {
    card.onAction();
  };

  const getTypeIcon = () => {
    switch (card.type) {
      case 'job':
        return <AntOutline />;
      case 'resume':
        return <CheckCircleOutline />;
      case 'interview':
        return <FaceRecognitionOutline />;
      default:
        return <AntOutline />;
    }
  };

  return (
    <div className={`action-card ${card.type}`}>
      <div className="card-icon">{getTypeIcon()}</div>
      <div className="card-content">
        <h4 className="card-title">{card.title}</h4>
        <p className="card-desc">{card.description}</p>
      </div>
      <Button
        size="small"
        color="primary"
        onClick={handleClick}
        className="card-action"
      >
        {card.actionText}
      </Button>
    </div>
  );
};

/**
 * 消息气泡组件
 */
const MessageBubble: React.FC<{
  message: Message;
}> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="avatar assistant-avatar">
          <FaceRecognitionOutline />
        </div>
      )}

      <div className="bubble-content">
        <div className="bubble-text">{message.content}</div>

        {message.actionCards && message.actionCards.length > 0 && (
          <div className="action-cards">
            {message.actionCards.map((card) => (
              <ActionCard key={card.id} card={card} />
            ))}
          </div>
        )}
      </div>

      {isUser && (
        <div className="avatar user-avatar">
          <UserOutline />
        </div>
      )}
    </div>
  );
};

/**
 * AI 职业顾问气泡组件
 */
const AIAdvisorBubble: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 初始欢迎消息
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setIsTyping(true);
      setTimeout(() => {
        setMessages([
          {
            id: '1',
            role: 'assistant',
            content: '您好！我是 HigherMatch 的 AI 职业顾问 🎯\n\n我可以帮您：\n• 分析简历匹配度\n• 推荐适合的职位\n• 提供面试技巧建议\n• 解答求职相关问题',
            actionCards: [
              {
                id: 'ac1',
                type: 'job',
                title: '查看最新推荐',
                description: '基于您的简历为您精选 5 个高匹配职位',
                actionText: '查看',
                onAction: () => {
                  Toast.show('跳转到职位推荐');
                },
              },
              {
                id: 'ac2',
                type: 'resume',
                title: '优化简历建议',
                description: 'AI 分析您的简历并给出优化建议',
                actionText: '开始',
                onAction: () => {
                  Toast.show('简历分析中...');
                },
              },
            ],
            timestamp: new Date(),
          },
        ]);
        setIsTyping(false);
      }, 1000);
    }
  }, [isOpen, messages.length]);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // 发送消息
  const handleSend = async () => {
    if (!message.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setMessage('');
    setIsTyping(true);

    // 模拟 AI 回复
    setTimeout(() => {
      const responses = [
        {
          content: '根据您的背景，我为您找到了 3 个非常匹配的职位。这些职位的 AI 匹配度都在 90% 以上 👍',
          cards: [
            {
              id: 'rc1',
              type: 'job' as const,
              title: '高级前端工程师 @ 字节跳动',
              description: '匹配度 96% · 35K-55K · 北京',
              actionText: '立即申请',
              onAction: () => Toast.show('跳转到申请页面'),
            },
            {
              id: 'rc2',
              type: 'job' as const,
              title: '前端架构师 @ 美团',
              description: '匹配度 93% · 40K-60K · 北京',
              actionText: '查看详情',
              onAction: () => Toast.show('跳转到职位详情'),
            },
          ],
        },
        {
          content: '您的简历整体不错！但我建议：\n\n1. 增加项目经验的量化数据\n2. 补充 Vue/React 框架的深入理解\n3. 突出团队协作和项目交付能力\n\n需要我帮您优化简历吗？',
          cards: [
            {
              id: 'rc3',
              type: 'resume' as const,
              title: 'AI 简历优化',
              description: '一键优化，提升简历竞争力',
              actionText: '开始优化',
              onAction: () => Toast.show('AI 正在优化您的简历...'),
            },
          ],
        },
        {
          content: '面试技巧建议：\n\n💡 技术面试准备：\n• 重点复习 React 原理和性能优化\n• 准备系统设计相关问题\n• 刷题建议：中等难度即可\n\n🗣️ 行为面试：\n• STAR 法则回答问题\n• 准备 2-3 个项目亮点案例',
          cards: [],
        },
      ];

      const randomResponse = responses[Math.floor(Math.random() * responses.length)];

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: randomResponse.content,
          actionCards: randomResponse.cards,
          timestamp: new Date(),
        },
      ]);
      setIsTyping(false);
    }, 1500);
  };

  // 键盘发送
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* 悬浮气泡按钮 */}
      <div
        className={`advisor-bubble ${isOpen ? 'hidden' : ''}`}
        onClick={() => setIsOpen(true)}
      >
        <AntOutline />
        <span className="bubble-badge">AI</span>
      </div>

      {/* 全屏对话框 */}
      <Dialog
        visible={isOpen}
        onClose={() => setIsOpen(false)}
        title={
          <div className="dialog-header">
            <FaceRecognitionOutline className="header-icon" />
            <span>AI 职业顾问</span>
          </div>
        }
        content={
          <div className="dialog-content">
            <div className="messages-container">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isTyping && (
                <div className="message-bubble assistant">
                  <div className="avatar assistant-avatar">
                    <FaceRecognitionOutline />
                  </div>
                  <div className="bubble-content">
                    <TypingIndicator />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-container">
              <input
                ref={inputRef as any}
                type="text"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="输入您的问题..."
                className="message-input"
              />
              <button
                onClick={handleSend}
                disabled={!message.trim()}
                className="send-btn"
              >
                <SendOutline />
              </button>
            </div>
          </div>
        }
        closeOnAction
        actions={[
          {
            key: 'close',
            text: '关闭',
            onClick: () => setIsOpen(false),
          },
        ]}
      />
    </>
  );
};

export default AIAdvisorBubble;
