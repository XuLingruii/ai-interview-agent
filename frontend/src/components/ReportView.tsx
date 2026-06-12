import { useMemo } from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';
import { useTheme } from '../useTheme';
import type { InterviewReport } from '../types';

interface Props { report: InterviewReport; onReset: () => void; }

const TYPE_LABELS: Record<string, string> = { project: '项目深挖', fundamentals: '基础八股', coding: '代码手撕', case_study: '案例分析' };

export default function ReportView({ report, onReset }: Props) {
  const { theme, toggle } = useTheme();
  const { metrics, rounds, llmReport } = report;

  const radarData = useMemo(() => {
    if (!rounds) return null;
    const breakdowns = rounds.filter((r) => r.detailedFeedback?.scoreBreakdown).map((r) => r.detailedFeedback!.scoreBreakdown);
    if (breakdowns.length === 0) return null;
    const keys = ['accuracy', 'depth', 'clarity', 'practicality'] as const;
    const labels: Record<string, string> = { accuracy: '准确度', depth: '深度', clarity: '表达清晰', practicality: '实践结合' };
    return keys.map((k) => ({ dimension: labels[k], score: Math.round((breakdowns.reduce((s, b) => s + (b[k] || 0), 0) / breakdowns.length) * 10) / 10, fullMark: 10 }));
  }, [rounds]);

  if (!metrics || !rounds) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="text-center space-y-4">
          <p className="text-[var(--text-muted)]">暂无面试数据，无法生成报告。</p>
          <button onClick={onReset} className="px-6 py-2.5 font-medium rounded-xl border" style={{ background: 'var(--bg-card)', color: 'var(--text)', borderColor: 'var(--border)' }}>
            返回首页
          </button>
        </div>
      </div>
    );
  }

  const cardClass = "border rounded-xl p-4";
  const cardStyle = { background: 'var(--bg-overlay)', borderColor: 'var(--border)' };

  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto space-y-8">
      <div className="flex justify-end gap-2">
        <button onClick={toggle} className="text-sm px-3 py-1.5 rounded-lg border border-[var(--border)] text-[var(--text-muted)] transition-colors">
          {theme === 'dark' ? '🌸 粉白' : '🌙 暗黑'}
        </button>
      </div>

      <div className="text-center">
        <h1 className="text-3xl font-bold text-[var(--text)] mb-2">面试复盘报告</h1>
        <p className="text-[var(--text-muted)]">{llmReport?.overallVerdict || '面试已完成'}</p>
      </div>

      <div className="grid grid-cols-5 gap-3">
        {[
          { label: '综合评分', value: `${metrics.overallScore}/10`, color: 'var(--text)' },
          { label: '薄弱点覆盖', value: `${metrics.weaknessCoverage}%`, color: 'var(--green)' },
          { label: '压力表现', value: metrics.depthAdaptability ? `${metrics.depthAdaptability}/10` : '—', color: 'var(--amber)' },
          { label: '知识真实度', value: metrics.knowledgeAuthenticity ? `${metrics.knowledgeAuthenticity}/10` : '—', color: 'var(--blue)' },
          { label: '提升轨迹', value: `${metrics.improvementTrajectory >= 0 ? '+' : ''}${metrics.improvementTrajectory}`, color: metrics.improvementTrajectory >= 0 ? 'var(--green)' : 'var(--red)' },
        ].map((m) => (
          <div key={m.label} className={cardClass + " text-center"} style={cardStyle}>
            <div className="text-2xl font-bold" style={{ color: m.color }}>{m.value}</div>
            <div className="text-xs mt-1 text-[var(--text-dim)]">{m.label}</div>
          </div>
        ))}
      </div>

      {radarData && (
        <div className={cardClass + " p-5"} style={cardStyle}>
          <h2 className="text-lg font-bold text-[var(--text)] mb-4">能力维度分析</h2>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: 'var(--text-muted)', fontSize: 13 }} />
              <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: 'var(--text-dim)', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8 }} labelStyle={{ color: 'var(--text)' }} />
              <Radar name="能力评分" dataKey="score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {llmReport?.strengthsSummary && (
          <div className={cardClass} style={{ ...cardStyle, borderColor: 'var(--green)' }}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--green)' }}>整体优势</h3>
            <ul className="space-y-2">
              {llmReport.strengthsSummary.map((s, i) => (
                <li key={i} className="text-sm text-[var(--text)] flex items-start gap-2"><span style={{ color: 'var(--green)' }}>+</span> {s}</li>
              ))}
            </ul>
          </div>
        )}
        {llmReport?.weaknessesSummary && (
          <div className={cardClass} style={{ ...cardStyle, borderColor: 'var(--red-border)' }}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--red)' }}>主要短板</h3>
            <ul className="space-y-2">
              {llmReport.weaknessesSummary.map((w, i) => (
                <li key={i} className="text-sm text-[var(--text)] flex items-start gap-2"><span style={{ color: 'var(--red)' }}>-</span> {w}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-bold text-[var(--text)]">逐题深度分析</h2>
        {rounds.map((r) => {
          const lr = llmReport?.detailedRoundAnalysis?.find((a) => a.roundNumber === r.roundNumber);
          return (
            <details key={r.roundNumber} className="border rounded-xl overflow-hidden group" style={{ background: 'var(--bg-overlay)', borderColor: 'var(--border)' }}>
              <summary className="px-5 py-4 cursor-pointer flex items-center gap-4 select-none" style={{ background: 'var(--bg-card-hover)' }}>
                <span className="text-lg font-bold" style={{ color: r.score >= 8 ? 'var(--green)' : r.score >= 6 ? 'var(--amber)' : 'var(--red)' }}>{r.score}/10</span>
                <span className="text-sm text-[var(--text)]">Q{r.roundNumber} · {TYPE_LABELS[r.questionType] || r.questionType}</span>
                <span className="text-xs text-[var(--text-dim)]">{r.topic}</span>
                <svg className="w-4 h-4 ml-auto group-open:rotate-180 transition-transform text-[var(--text-dim)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" /></svg>
              </summary>
              <div className="px-5 pb-4 space-y-3 pt-3" style={{ borderColor: 'var(--border)', borderTop: '1px solid var(--border)' }}>
                <p className="text-xs text-[var(--text-dim)]">Q: {r.question}</p>
                <p className="text-xs text-[var(--text-dim)]">A: {r.answer}</p>
                {lr?.gapAnalysis && <div><span className="text-xs font-semibold" style={{ color: 'var(--amber)' }}>差距分析</span><p className="text-sm text-[var(--text)] mt-1">{lr.gapAnalysis}</p></div>}
                {lr?.thinkingFramework && <div><span className="text-xs font-semibold" style={{ color: 'var(--blue)' }}>思维框架</span><p className="text-sm text-[var(--text)] mt-1">{lr.thinkingFramework}</p></div>}
                {lr?.modelResponse && (
                  <div><span className="text-xs font-semibold" style={{ color: 'var(--green)' }}>理想回答应包含</span>
                    <ul className="mt-1 space-y-1">{(Array.isArray(lr.modelResponse) ? lr.modelResponse : [lr.modelResponse]).map((p, i) => <li key={i} className="text-sm text-[var(--text)] flex gap-2"><span style={{ color: 'var(--green)' }}>{i + 1}.</span> {p}</li>)}</ul>
                  </div>
                )}
                {r.detailedFeedback?.recommendedResources && (
                  <div><span className="text-xs font-semibold" style={{ color: 'var(--purple)' }}>推荐学习</span>
                    <ul className="mt-1 space-y-1">{r.detailedFeedback.recommendedResources.map((res, i) => <li key={i} className="text-sm text-[var(--text)]">→ {res}</li>)}</ul>
                  </div>
                )}
                {r.detailedFeedback?.modelAnswerOutline && !lr?.modelResponse && (
                  <div><span className="text-xs font-semibold" style={{ color: 'var(--green)' }}>建议答题框架</span>
                    <ol className="mt-1 space-y-1">{r.detailedFeedback.modelAnswerOutline.map((step, i) => <li key={i} className="text-sm text-[var(--text)]">{i + 1}. {step}</li>)}</ol>
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>

      {llmReport?.improvementPlan && llmReport.improvementPlan.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xl font-bold text-[var(--text)]">提升计划</h2>
          {llmReport.improvementPlan.map((plan, i) => (
            <div key={i} className={cardClass} style={cardStyle}>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: plan.priority === '高' ? 'var(--red-bg)' : plan.priority === '中' ? 'var(--amber-bg)' : 'var(--accent-bg)', color: plan.priority === '高' ? 'var(--red)' : plan.priority === '中' ? 'var(--amber)' : 'var(--text-muted)' }}>{plan.priority}优先级</span>
                <span className="text-sm font-semibold text-[var(--text)]">{plan.area}</span>
                {plan.estimatedTimeframe && <span className="text-xs text-[var(--text-dim)] ml-auto">{plan.estimatedTimeframe}</span>}
              </div>
              <ul className="space-y-1">{plan.actionItems.map((item, j) => <li key={j} className="text-sm text-[var(--text)] flex gap-2"><span style={{ color: 'var(--accent)' }}>→</span> {item}</li>)}</ul>
            </div>
          ))}
        </div>
      )}

      {llmReport?.nextInterviewPrep && (llmReport.nextInterviewPrep.focusAreas?.length || llmReport.nextInterviewPrep.resources?.length) ? (
        <div className="border rounded-xl p-5" style={{ background: 'var(--accent-bg)', borderColor: 'var(--border-accent)' }}>
          <h2 className="text-lg font-bold mb-3" style={{ color: 'var(--accent)' }}>下次面试建议</h2>
          {llmReport.nextInterviewPrep.focusAreas && (
            <div className="mb-3"><span className="text-xs text-[var(--text-muted)]">重点方向</span>
              <div className="flex flex-wrap gap-2 mt-1">{llmReport.nextInterviewPrep.focusAreas.map((f, i) => <span key={i} className="text-xs px-2 py-1 rounded-full" style={{ background: 'var(--accent-bg)', color: 'var(--accent)' }}>{f}</span>)}</div>
            </div>
          )}
          {llmReport.nextInterviewPrep.resources && (
            <div><span className="text-xs text-[var(--text-muted)]">推荐资源</span>
              <ul className="mt-1 space-y-1">{llmReport.nextInterviewPrep.resources.map((r, i) => <li key={i} className="text-sm text-[var(--text)]">→ {r}</li>)}</ul>
            </div>
          )}
        </div>
      ) : null}

      <div className="text-center pb-8">
        <button onClick={onReset} className="px-6 py-2.5 font-medium rounded-xl transition-colors border" style={{ background: 'var(--bg-card)', color: 'var(--text)', borderColor: 'var(--border)' }}>
          开始新的面试
        </button>
      </div>
    </div>
  );
}
