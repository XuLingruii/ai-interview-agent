interface Props {
  currentRound: number; maxRounds: number;
  score: number | null; weaknessCovered: number; weaknessTotal: number;
  depth: number; questionType: string;
  typeCounts: { project: number; fundamentals: number; coding: number; case_study: number };
  codingDone: boolean;
  caseStudyDone: boolean;
}

const TYPE_LABELS: Record<string, string> = { project: '项目深挖', fundamentals: '基础八股', coding: '代码手撕', case_study: '案例分析' };
const DEPTH_LABELS: Record<number, string> = { 1: '基础摸底', 2: '深入追问', 3: '压力测试' };

export default function ScorePanel({ currentRound, maxRounds, score, weaknessCovered, weaknessTotal, depth, questionType, typeCounts, codingDone, caseStudyDone }: Props) {
  const progress = maxRounds > 0 ? (currentRound / maxRounds) * 100 : 0;
  const wProgress = weaknessTotal > 0 ? (weaknessCovered / weaknessTotal) * 100 : 0;

  return (
    <div className="w-64 border rounded-xl p-4 space-y-5 shrink-0" style={{ background: 'var(--bg-overlay)', borderColor: 'var(--border)' }}>
      <h3 className="text-sm font-semibold text-center text-[var(--text-muted)]">实时面板</h3>

      <div>
        <div className="flex justify-between text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
          <span>当前轮次</span><span>{currentRound}/{maxRounds}</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-input)' }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${progress}%`, background: 'var(--accent)' }} />
        </div>
      </div>

      <div className="text-center">
        <div className="text-3xl font-bold text-[var(--text)]">{score !== null ? score.toFixed(1) : '—'}</div>
        <div className="text-xs text-[var(--text-dim)]">当前均分</div>
      </div>

      <div>
        <div className="flex justify-between text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
          <span>薄弱点覆盖</span><span>{weaknessCovered}/{weaknessTotal}</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--bg-input)' }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${wProgress}%`, background: 'var(--green)' }} />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-muted)]">当前深度</span>
          <span className="font-medium" style={{ color: 'var(--accent)' }}>{DEPTH_LABELS[depth] || `深度${depth}`}</span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-muted)]">题目类型</span>
          <span className="font-medium" style={{ color: 'var(--amber)' }}>{TYPE_LABELS[questionType] || questionType}</span>
        </div>
      </div>

      <div>
        <div className="text-xs mb-2 text-[var(--text-dim)]">已问类型分布</div>
        <div className="space-y-1.5">
          {[
            { type: 'project', label: '项目深挖', color: 'var(--blue)', count: typeCounts.project },
            { type: 'fundamentals', label: '基础八股', color: 'var(--amber)', count: typeCounts.fundamentals },
            { type: 'coding', label: '代码手撕', color: 'var(--red)', count: typeCounts.coding, done: codingDone },
            { type: 'case_study', label: '案例分析', color: 'var(--purple)', count: typeCounts.case_study, done: caseStudyDone },
          ].map(({ type, label, color, count, done }) => (
            <div key={type} className="flex items-center gap-2">
              <span className="text-[10px] text-[var(--text-dim)] w-12">{label}</span>
              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-input)' }}>
                <div className="h-full rounded-full transition-all" style={{ width: `${maxRounds > 1 ? (count / (currentRound - 1 || 1)) * 100 : 0}%`, background: color }} />
              </div>
              <span className="text-[10px] text-[var(--text-dim)] w-3 text-right">{count}</span>
              {done !== undefined && done && <span className="text-[10px]" style={{ color: 'var(--green)' }}>✓</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
