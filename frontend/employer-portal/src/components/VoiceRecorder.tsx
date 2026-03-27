/**
 * HigherMatch™ Employer Portal - 语音录入组件
 * ============================================
 * 使用 WebRTC MediaRecorder API 实现语音录入
 * 包含 Canvas 波形动画
 *
 * 版本: 1.0.0
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button, Space, Typography, message, Spin } from 'antd';
import { AudioOutlined, StopOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons';
import { apiClient } from '../api/client';

const { Text, Title } = Typography;

interface VoiceRecorderProps {
  onTranscriptionComplete?: (text: string) => void;
  placeholder?: string;
}

interface AudioData {
  base64: string;
  duration: number;
}

/**
 * 语音录入组件
 * 支持录音、波形可视化、转文字
 */
const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  onTranscriptionComplete,
  placeholder = '点击录音按钮开始录入需求...',
}) => {
  // 状态
  const [isRecording, setIsRecording] = useState(false);
  const [audioData, setAudioData] = useState<AudioData | null>(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordedText, setRecordedText] = useState<string>('');
  const [isPaused, setIsPaused] = useState(false);

  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);

  // 初始化音频上下文和分析器
  const initAudioContext = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // 创建 MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      // 设置音频分析
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);
      analyserRef.current = analyser;

      // MediaRecorder 事件
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          const duration = (Date.now() - startTimeRef.current) / 1000;
          setAudioData({ base64, duration });
        };
        reader.readAsDataURL(blob);
      };

      return true;
    } catch (error) {
      console.error('初始化音频失败:', error);
      message.error('无法访问麦克风，请检查权限设置');
      return false;
    }
  }, []);

  // 绘制波形
  const drawWaveform = useCallback(() => {
    if (!canvasRef.current || !analyserRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteTimeDomainData(dataArray);

    // 设置画布尺寸
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    // 清空画布
    ctx.fillStyle = 'rgba(240, 246, 255, 1)';
    ctx.fillRect(0, 0, rect.width, rect.height);

    // 绘制波形
    ctx.lineWidth = 2;
    ctx.strokeStyle = isRecording ? '#ff4d4f' : '#1890ff';
    ctx.beginPath();

    const sliceWidth = rect.width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = (v * rect.height) / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    ctx.lineTo(rect.width, rect.height / 2);
    ctx.stroke();

    // 继续动画
    animationFrameRef.current = requestAnimationFrame(drawWaveform);
  }, [isRecording]);

  // 开始录音
  const startRecording = async () => {
    const success = await initAudioContext();
    if (success && mediaRecorderRef.current) {
      mediaRecorderRef.current.start(100);
      startTimeRef.current = Date.now();
      setIsRecording(true);
      setIsPaused(false);
      setAudioData(null);
      setRecordedText('');
      message.success('开始录音');

      // 开始绘制波形
      drawWaveform();
    }
  };

  // 停止录音
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);

      // 停止波形动画
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      // 停止所有 tracks
      mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());

      // 关闭音频上下文
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }

      message.info('录音已停止');
    }
  };

  // 发送转写请求
  const handleTranscribe = async () => {
    if (!audioData) {
      message.warning('请先录音');
      return;
    }

    setIsTranscribing(true);
    try {
      const response = await apiClient.post<{ text: string }>('/api/v1/voice/transcribe', {
        audio: audioData.base64,
        duration: audioData.duration,
      });

      setRecordedText(response.text);
      message.success('转写完成');

      if (onTranscriptionComplete) {
        onTranscriptionComplete(response.text);
      }
    } catch (error) {
      console.error('转写失败:', error);
      message.error('转写失败，请重试');
    } finally {
      setIsTranscribing(false);
    }
  };

  // 删除录音
  const handleDelete = () => {
    setAudioData(null);
    setRecordedText('');
    message.info('已清除录音');
  };

  // 清理
  useEffect(() => {
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return (
    <div className="voice-recorder">
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 波形画布 */}
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: 120,
            borderRadius: 8,
            overflow: 'hidden',
            background: '#f0f6ff',
            border: `2px solid ${isRecording ? '#ff4d4f' : '#d9d9d9'}`,
            transition: 'all 0.3s ease',
          }}
        >
          <canvas
            ref={canvasRef}
            style={{
              width: '100%',
              height: '100%',
              display: 'block',
            }}
          />

          {/* 录音指示器 */}
          {isRecording && (
            <div
              style={{
                position: 'absolute',
                top: 8,
                right: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: '#ff4d4f',
                  animation: 'pulse 1s infinite',
                }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                录音中...
              </Text>
            </div>
          )}

          {/* 提示文字 */}
          {!isRecording && !audioData && (
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
              }}
            >
              <AudioOutlined style={{ fontSize: 32, color: '#d9d9d9' }} />
              <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                {placeholder}
              </Text>
            </div>
          )}

          {/* 录音时长 */}
          {audioData && (
            <div
              style={{
                position: 'absolute',
                top: 8,
                left: 8,
              }}
            >
              <Text style={{ fontSize: 12, color: '#52c41a' }}>
                已录制 {audioData.duration.toFixed(1)}秒
              </Text>
            </div>
          )}
        </div>

        {/* 控制按钮 */}
        <Space size="middle" style={{ width: '100%', justifyContent: 'center' }}>
          {!isRecording ? (
            <Button
              type="primary"
              size="large"
              icon={<AudioOutlined />}
              onClick={startRecording}
              danger
              style={{
                width: 120,
                height: 48,
                borderRadius: 24,
                fontSize: 16,
              }}
            >
              开始录音
            </Button>
          ) : (
            <Button
              type="primary"
              size="large"
              icon={<StopOutlined />}
              onClick={stopRecording}
              style={{
                width: 120,
                height: 48,
                borderRadius: 24,
                fontSize: 16,
                background: '#ff4d4f',
                borderColor: '#ff4d4f',
              }}
            >
              停止录音
            </Button>
          )}

          {audioData && !recordedText && (
            <>
              <Button
                size="large"
                icon={<DeleteOutlined />}
                onClick={handleDelete}
              >
                删除
              </Button>
              <Button
                type="primary"
                size="large"
                icon={isTranscribing ? <Spin size="small" /> : <SendOutlined />}
                onClick={handleTranscribe}
                disabled={isTranscribing}
              >
                {isTranscribing ? '转写中...' : '转写'}
              </Button>
            </>
          )}
        </Space>

        {/* 转写结果 */}
        {recordedText && (
          <div
            style={{
              padding: 16,
              background: '#f6ffed',
              borderRadius: 8,
              border: '1px solid #b7eb8f',
            }}
          >
            <Title level={5} style={{ marginBottom: 8 }}>
              转写结果
            </Title>
            <Text style={{ whiteSpace: 'pre-wrap' }}>{recordedText}</Text>
            <div style={{ marginTop: 12 }}>
              <Button
                type="link"
                icon={<DeleteOutlined />}
                onClick={handleDelete}
              >
                重新录音
              </Button>
            </div>
          </div>
        )}
      </Space>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default VoiceRecorder;
