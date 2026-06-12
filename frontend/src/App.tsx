import { useState, useCallback } from 'react';
import ConfigPanel from './components/ConfigPanel';
import InterviewChat from './components/InterviewChat';
import ReportView from './components/ReportView';
import type { StartResponse, InterviewReport } from './types';

type Phase = 'config' | 'interview' | 'report';

export default function App() {
  const [phase, setPhase] = useState<Phase>('config');
  const [loading, setLoading] = useState(false);
  const [startData, setStartData] = useState<StartResponse | null>(null);
  const [report, setReport] = useState<InterviewReport | null>(null);

  const handleStart = useCallback(async (resume: string, jd: string, maxRounds: number) => {
    setLoading(true);
    try {
      const res = await fetch('/api/interview/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resume, jd, maxRounds }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert('启动失败: ' + (err.detail || '未知错误'));
        return;
      }
      const data: StartResponse = await res.json();
      setStartData(data);
      setPhase('interview');
    } catch (e) {
      alert('网络错误: ' + String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleComplete = useCallback((report: InterviewReport) => {
    setReport(report);
    setPhase('report');
  }, []);

  const handleReset = useCallback(() => {
    setPhase('config');
    setStartData(null);
    setReport(null);
  }, []);

  const handleViewHistoryReport = useCallback(async (historySessionId: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/interview/report/${historySessionId}`);
      if (!res.ok) {
        alert('加载历史报告失败');
        return;
      }
      const data: InterviewReport = await res.json();
      setReport(data);
      setPhase('report');
    } catch {
      alert('网络错误');
    } finally {
      setLoading(false);
    }
  }, []);

  if (phase === 'config') {
    return <ConfigPanel onStart={handleStart} onViewHistoryReport={handleViewHistoryReport} loading={loading} />;
  }

  if (phase === 'interview' && startData) {
    return (
      <InterviewChat
        startData={startData}
        onComplete={handleComplete}
      />
    );
  }

  if (phase === 'report' && report) {
    return <ReportView report={report} onReset={handleReset} />;
  }

  return null;
}
