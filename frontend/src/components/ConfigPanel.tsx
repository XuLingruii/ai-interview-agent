import { useState, useRef, useEffect, type FormEvent } from 'react';
import { useTheme } from '../useTheme';
import HistoryPanel from './HistoryPanel';

interface Props {
  onStart: (resume: string, jd: string, maxRounds: number) => void;
  onViewHistoryReport: (sessionId: string) => void;
  loading: boolean;
}

export default function ConfigPanel({ onStart, onViewHistoryReport, loading }: Props) {
  const { theme, toggle } = useTheme();
  const [resume, setResume] = useState(() => localStorage.getItem('interview-resume') || '');
  const [jd, setJd] = useState(() => localStorage.getItem('interview-jd') || '');
  const [maxRounds, setMaxRounds] = useState(() => {
    const v = localStorage.getItem('interview-maxRounds');
    return v ? Number(v) : 8;
  });
  const [uploading, setUploading] = useState(false);
  const [uploadFileName, setUploadFileName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadFileName(file.name);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/parse-resume', { method: 'POST', body: formData });
      if (!res.ok) {
        const text = await res.text();
        let msg = text;
        try { msg = JSON.parse(text).detail || text; } catch { /* JSON parse failed, use raw text */ }
        alert('文件解析失败: ' + msg);
        return;
      }
      const data = await res.json();
      setResume(data.text);
    } catch (err) {
      alert('上传失败: ' + String(err));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  useEffect(() => { localStorage.setItem('interview-resume', resume); }, [resume]);
  useEffect(() => { localStorage.setItem('interview-jd', jd); }, [jd]);
  useEffect(() => { localStorage.setItem('interview-maxRounds', String(maxRounds)); }, [maxRounds]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onStart(resume, jd, maxRounds);
  };

  const inputClass = "w-full bg-[var(--bg-input)] border border-[var(--border)] rounded-[var(--radius)] p-3 text-[var(--text)] text-sm resize-none focus:outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-dim)]";
  const labelClass = "block text-sm text-[var(--text-muted)] mb-1";
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl bg-[var(--bg-overlay)] border border-[var(--border)] rounded-[var(--radius-xl)] p-8 space-y-6"
      >
        <div className="flex items-center justify-between">
          <div />
          <div className="text-center flex-1">
            <h1 className="text-3xl font-bold text-[var(--text)] mb-2">AI 面试模拟</h1>
            <p className="text-[var(--text-muted)]">基于 ReAct 范式的智能面试官</p>
          </div>
          <button
            type="button"
            onClick={toggle}
            className="text-sm px-3 py-1.5 rounded-lg border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)] bg-[var(--bg-card)] transition-colors shrink-0"
            title="切换配色"
          >
            {theme === 'dark' ? '🌸' : '🌙'}
          </button>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className={labelClass}>简历内容</label>
            <div className="flex items-center gap-2">
              <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md" onChange={handleFileUpload} className="hidden" />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="text-xs border border-[var(--border-accent)] rounded-lg px-2.5 py-1 transition-colors disabled:opacity-50"
                style={{ color: 'var(--accent)' }}
              >
                {uploading ? '解析中...' : '📄 上传PDF简历'}
              </button>
              {uploadFileName && (
                <span className="text-xs text-[var(--text-dim)] truncate max-w-[120px]">{uploadFileName}</span>
              )}
            </div>
          </div>
          <textarea
            className={inputClass + " h-32"}
            value={resume}
            onChange={(e) => setResume(e.target.value)}
            placeholder="粘贴简历内容或上传PDF..."
          />
        </div>

        <div>
          <label className={labelClass}>岗位 JD</label>
          <textarea
            className={inputClass + " h-24"}
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="粘贴岗位描述..."
          />
        </div>

        <div className="flex items-center gap-4">
          <div>
            <label className={labelClass}>轮数</label>
            <input
              type="number"
              min={3} max={30}
              value={maxRounds}
              onChange={(e) => setMaxRounds(Math.max(3, Math.min(30, Number(e.target.value) || 3)))}
              className="w-20 bg-[var(--bg-input)] border border-[var(--border)] rounded-lg px-3 py-2 text-[var(--text)] text-sm focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !resume.trim() || !jd.trim()}
          className="w-full py-3 font-semibold rounded-[var(--radius-lg)] transition-colors disabled:opacity-40"
          style={{ background: 'var(--accent)', color: '#fff' }}
        >
          {loading ? '正在分析简历和JD...' : '开始面试'}
        </button>

        <div className="border-t pt-5" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-[var(--text-muted)]">历史面试记录</h2>
          </div>
          <HistoryPanel onViewReport={onViewHistoryReport} refreshKey={0} />
        </div>
      </form>
    </div>
  );
}
