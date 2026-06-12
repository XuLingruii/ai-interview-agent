import { useState, useRef, useEffect, useCallback } from 'react';
import { useTheme } from '../useTheme';
import { useSSE } from '../hooks/useSSE';
import VoiceInput from './VoiceInput';
import AudioOutput from './AudioOutput';
import ScorePanel from './ScorePanel';
import type { StartResponse, InterviewReport } from '../types';

interface SSEEventData {
  type: string;
  round?: number;
  score?: number;
  feedback?: string;
  depth?: number;
  questionType?: string;
  topic?: string;
  content?: string;
  evaluation?: { score: number; feedback: string };
  report?: InterviewReport;
  message?: string;
}

interface Message {
  role: 'interviewer' | 'user' | 'system';
  content: string;
  round?: number;
  score?: number;
  feedback?: string;
  questionType?: string;
  topic?: string;
}

interface Props {
  startData: StartResponse;
  onComplete: (report: InterviewReport) => void;
}

const TYPE_LABELS: Record<string, string> = {
  project: '项目深挖', fundamentals: '基础八股', coding: '代码手撕', case_study: '案例分析',
};

const STATUS_LABELS: Record<string, string> = {
  evaluating: '正在评分...',
  evaluated: '评分完成',
  analyzing: '正在详细分析...',
  deciding_next: '决定下一题方向...',
  generating_question: '正在出题...',
  question_type_decided: '已选题型',
  generating_report: '正在生成复盘报告...',
};

export default function InterviewChat({ startData, onComplete }: Props) {
  const { toggle } = useTheme();
  const [messages, setMessages] = useState<Message[]>(() => {
    const first = startData.firstQuestion;
    return [{ role: 'interviewer', content: first.content, round: first.round, questionType: first.questionType, topic: first.topic }];
  });
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState<string>('');
  const [scores, setScores] = useState<number[]>([]);
  const [currentRound, setCurrentRound] = useState(1);
  const [currentDepth, setCurrentDepth] = useState(1);
  const [currentQuestionType, setCurrentQuestionType] = useState('project');
  const [weaknessCovered] = useState(0);
  const [weaknessTotal] = useState(startData.analysis.weakPoints.length);
  const [typeCounts, setTypeCounts] = useState({ project: 0, fundamentals: 0, coding: 0, case_study: 0 });
  const [codingDone, setCodingDone] = useState(false);
  const [caseStudyDone, setCaseStudyDone] = useState(false);
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [latestQuestion, setLatestQuestion] = useState(startData.firstQuestion.content);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const sessionIdRef = useRef(startData.sessionId);

  const handleSSEEvent = useCallback((event: string, data: unknown) => {
    const d = data as SSEEventData;
    switch (event) {
      case 'evaluating':
      case 'analyzing':
      case 'deciding_next':
      case 'generating_question':
      case 'generating_report':
        setStreamingStatus(STATUS_LABELS[event] || event);
        break;

      case 'evaluated':
        if (d.score != null) {
          setScores((prev) => [...prev, d.score!]);
        }
        setStreamingStatus('');
        break;

      case 'question_type_decided':
        break;

      case 'question':
        setStreamingStatus('');
        if (d.evaluation) {
          const feedbackMsg = d.evaluation.feedback || '';
          if (feedbackMsg) {
            setMessages((prev) => {
              const updated = [...prev];
              const lastBot = [...updated].reverse().findIndex((m) => m.role === 'interviewer');
              if (lastBot !== -1) {
                const idx = updated.length - 1 - lastBot;
                updated[idx] = { ...updated[idx], score: d.evaluation!.score, feedback: feedbackMsg };
              }
              return updated;
            });
          }
        }
        if (d.content) {
          setMessages((prev) => [...prev, {
            role: 'interviewer' as const,
            content: d.content!,
            round: d.round,
            questionType: d.questionType,
            topic: d.topic,
          }]);
          setCurrentRound(d.round ?? currentRound);
          setCurrentDepth(d.depth ?? currentDepth);
          setCurrentQuestionType(d.questionType ?? currentQuestionType);
          setLatestQuestion(d.content!);
          const qt = d.questionType ?? 'project';
          if (qt === 'project' || qt === 'fundamentals' || qt === 'coding' || qt === 'case_study') {
            setTypeCounts((prev) => ({ ...prev, [qt]: prev[qt] + 1 }));
            if (qt === 'coding') setCodingDone(true);
            if (qt === 'case_study') setCaseStudyDone(true);
          }
        }
        break;

      case 'completed':
        setStreamingStatus('');
        if (d.report) onComplete(d.report);
        break;
    }
  // currentRound/currentDepth/currentQuestionType are fallback defaults, not deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onComplete]);

  useSSE(startData.sessionId, handleSSEEvent);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streamingStatus]);

  const handleSend = async (text?: string) => {
    const answer = (text || input).trim();
    if (!answer || sending) return;
    setMessages((prev) => [...prev, { role: 'user', content: answer }]);
    setInput('');
    setSending(true);
    setStreamingStatus('evaluating');

    try {
      await fetch('/api/interview/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId: sessionIdRef.current, answer }),
      });
      // Response comes via SSE — no need to parse the POST response
    } catch {
      setStreamingStatus('');
      setMessages((prev) => [...prev, { role: 'system', content: '网络错误，请重试' }]);
    } finally {
      setSending(false);
    }
  };

  const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null;

  const userMsgClass = "max-w-[80%] rounded-2xl px-4 py-3 border";
  const userMsgStyle = { background: 'var(--accent-bg)', borderColor: 'var(--border-accent)' };
  const botMsgStyle = { background: 'var(--bg-card)', borderColor: 'var(--border)' };

  return (
    <div className="flex gap-6 h-screen p-6 max-w-7xl mx-auto">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-4 mb-4">
          <h2 className="text-lg font-semibold text-[var(--text)] shrink-0">
            面试中 · {startData.analysis.jd?.level || '校招'}
          </h2>
          <AudioOutput text={latestQuestion} />
          <div className="flex-1" />
          <button onClick={() => setShowEndConfirm(true)} className="text-xs border rounded-lg px-3 py-1 transition-colors" style={{ color: 'var(--red)', borderColor: 'var(--red-border)' }}>
            结束面试
          </button>
          <button onClick={toggle} className="text-sm px-2 py-1 rounded-lg border border-[var(--border)] text-[var(--text-muted)] transition-colors" title="切换配色">
            🌓
          </button>
          <span className="text-xs text-[var(--text-dim)]">匹配度 {startData.analysis.matchScore}%</span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={userMsgClass} style={msg.role === 'user' ? userMsgStyle : botMsgStyle}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-[var(--text-muted)]">
                    {msg.role === 'interviewer' ? '🤖 面试官' : msg.role === 'system' ? '⚠️' : '👤 你'}
                  </span>
                  {msg.round && <span className="text-[10px] text-[var(--text-dim)]">Q{msg.round} · {TYPE_LABELS[msg.questionType || ''] || msg.questionType}{msg.topic ? ` · ${msg.topic}` : ''}</span>}
                  {msg.score !== undefined && (
                    <span className="text-[10px] font-bold ml-auto" style={{ color: msg.score >= 8 ? 'var(--green)' : msg.score >= 6 ? 'var(--amber)' : 'var(--red)' }}>
                      {msg.score}/10
                    </span>
                  )}
                </div>
                <p className="text-sm text-[var(--text)] whitespace-pre-wrap">{msg.content}</p>
                {msg.feedback && <p className="text-xs text-[var(--text-muted)] mt-2 pt-2 border-t border-[var(--border)]">{msg.feedback}</p>}
              </div>
            </div>
          ))}
          {streamingStatus && (
            <div className="flex justify-start">
              <div className="rounded-2xl px-4 py-3 flex items-center gap-3" style={botMsgStyle}>
                <div className="flex gap-1">
                  {[1, 2, 3].map((i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--accent)', animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
                <span className="text-xs text-[var(--text-muted)]">{streamingStatus}</span>
              </div>
            </div>
          )}
          {sending && !streamingStatus && (
            <div className="flex justify-start">
              <div className="rounded-2xl px-4 py-3" style={botMsgStyle}>
                <div className="flex gap-1">
                  {[1, 2, 3].map((i) => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full animate-bounce" style={{ background: 'var(--text-dim)', animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="flex items-end gap-2">
          <VoiceInput onTranscript={(t) => setInput((p) => p + t)} />
          <textarea
            className="flex-1 bg-[var(--bg-input)] border border-[var(--border)] rounded-xl p-3 text-[var(--text)] text-sm resize-none focus:outline-none focus:border-[var(--accent)]"
            rows={2} value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="输入你的回答... (Enter 发送, Shift+Enter 换行)" disabled={sending}
          />
          <button
            onClick={() => handleSend()}
            disabled={sending || !input.trim()}
            className="px-5 py-2.5 font-medium rounded-xl transition-colors disabled:opacity-40"
            style={{ background: 'var(--accent)', color: '#fff' }}
          >发送</button>
        </div>
      </div>

      <ScorePanel
        currentRound={currentRound} maxRounds={startData.maxRounds}
        score={avgScore} weaknessCovered={weaknessCovered} weaknessTotal={weaknessTotal}
        depth={currentDepth} questionType={currentQuestionType}
        typeCounts={typeCounts} codingDone={codingDone} caseStudyDone={caseStudyDone}
      />

      {showEndConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowEndConfirm(false)}>
          <div className="rounded-2xl p-6 w-80 shadow-2xl" style={{ background: 'var(--bg)' }} onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text)' }}>结束面试</h3>
            <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>确定要结束面试吗？将生成当前进度的复盘报告。</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowEndConfirm(false)} className="px-4 py-2 rounded-lg text-sm border transition-colors" style={{ borderColor: 'var(--border)', color: 'var(--text)' }}>取消</button>
              <button onClick={async () => {
                setShowEndConfirm(false);
                setSending(true);
                const res = await fetch('/api/interview/end', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ sessionId: sessionIdRef.current, answer: '' }),
                });
                if (res.ok) { const data = await res.json(); onComplete(data.report); }
                setSending(false);
              }} className="px-4 py-2 rounded-lg text-sm text-white transition-colors" style={{ background: 'var(--red)' }}>确定结束</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
