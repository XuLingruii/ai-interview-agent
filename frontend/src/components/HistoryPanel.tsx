import { useState, useEffect, useCallback } from 'react';

interface SessionSummary {
  sessionId: string;
  createdAt: string;
  completedAt: string;
  totalRounds: number;
  maxRounds: number;
  overallScore: number | null;
  weaknessCoverage: number | null;
  status: string;
}

interface Props {
  onViewReport: (sessionId: string) => void;
  refreshKey: number;
}

function formatDate(iso: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export default function HistoryPanel({ onViewReport, refreshKey }: Props) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/history');
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      setSessions(data);
    } catch {
      setError('加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- fetchHistory is async via useCallback
  useEffect(() => { void fetchHistory(); }, [fetchHistory, refreshKey]);

  const handleDelete = async (sessionId: string) => {
    setDeleting(sessionId);
    try {
      const res = await fetch(`/api/history/${sessionId}`, { method: 'DELETE' });
      if (!res.ok) {
        const text = await res.text();
        console.error(`[HistoryPanel] DELETE ${sessionId} failed: ${res.status} ${text}`);
        alert(`删除失败 (${res.status})`);
        return;
      }
      setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));
    } catch (err) {
      console.error(`[HistoryPanel] DELETE ${sessionId} error:`, err);
      alert('删除失败，请检查网络连接');
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-6">
        <span className="text-sm text-[var(--text-dim)]">加载历史记录...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-6">
        <span className="text-xs text-[var(--red)]">{error}</span>
        <button onClick={fetchHistory} className="ml-2 text-xs underline" style={{ color: 'var(--accent)' }}>重试</button>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="text-center py-6">
        <span className="text-sm text-[var(--text-dim)]">暂无历史面试记录</span>
        <p className="text-xs text-[var(--text-dim)] mt-1">完成一次面试后会自动保存</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
        {sessions.map((s) => (
          <div
            key={s.sessionId}
            className="flex items-center gap-3 rounded-lg px-4 py-3 border transition-colors cursor-pointer"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
            onClick={() => onViewReport(s.sessionId)}
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[var(--text)] truncate">
                  {s.completedAt ? '已完成' : '未完成'} · {s.totalRounds}/{s.maxRounds}轮
                </span>
                {s.overallScore != null && (
                  <span className="text-xs font-bold px-1.5 py-0.5 rounded" style={{
                    background: s.overallScore >= 7 ? 'var(--green-bg)' : s.overallScore >= 5 ? 'var(--amber-bg)' : 'var(--red-bg)',
                    color: s.overallScore >= 7 ? 'var(--green)' : s.overallScore >= 5 ? 'var(--amber)' : 'var(--red)',
                  }}>
                    {s.overallScore}/10
                  </span>
                )}
                {s.weaknessCoverage != null && (
                  <span className="text-[10px] text-[var(--text-dim)]">覆盖{s.weaknessCoverage}%</span>
                )}
              </div>
              <div className="text-[10px] text-[var(--text-dim)] mt-0.5">{formatDate(s.createdAt)}</div>
            </div>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setConfirmTarget(s.sessionId); }}
              disabled={deleting === s.sessionId}
              className="text-xs px-2 py-1 rounded border border-[var(--border)] transition-colors shrink-0 disabled:opacity-40 hover:border-[var(--red-border)]"
              style={{ color: 'var(--text-dim)' }}
              title="删除记录"
            >
              {deleting === s.sessionId ? '...' : '✕'}
            </button>
          </div>
        ))}
      </div>

      {/* Confirm dialog */}
      {confirmTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={() => setConfirmTarget(null)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <div
            className="relative rounded-2xl p-6 w-80 shadow-2xl border animate-in slide-in-from-bottom-4 duration-200"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: 'var(--red-bg)' }}>
                <svg className="w-4 h-4" style={{ color: 'var(--red)' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M5.07 19H18.93A2 2 0 0020 16.57l-4.53-10.14a2 2 0 00-3.54 0L7.37 16.57A2 2 0 008.07 19z" />
                </svg>
              </div>
              <h3 className="text-sm font-semibold text-[var(--text)]">确认删除</h3>
            </div>
            <p className="text-sm text-[var(--text-muted)] mb-5 leading-relaxed">
              此操作不可撤销。确定要删除这条面试记录和复盘报告吗？
            </p>
            <div className="flex gap-3 justify-end">
              <button
                type="button"
                onClick={() => setConfirmTarget(null)}
                className="px-4 py-2 text-sm rounded-lg border border-[var(--border)] text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-card-hover)]"
              >
                取消
              </button>
              <button
                type="button"
                onClick={() => { handleDelete(confirmTarget); setConfirmTarget(null); }}
                className="px-4 py-2 text-sm font-medium rounded-lg text-white transition-colors"
                style={{ background: 'var(--red)' }}
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
