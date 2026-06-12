import { useEffect, useRef } from 'react';
import { useSpeechSynthesis } from '../hooks/useSpeechSynthesis';

interface Props { text: string | null; }

export default function AudioOutput({ text }: Props) {
  const { speak, isSpeaking, isSupported, muted, setMuted, rate, setRate } = useSpeechSynthesis();
  const lastTextRef = useRef('');
  useEffect(() => { if (text && text !== lastTextRef.current) { lastTextRef.current = text; speak(text); } }, [text, speak]);
  if (!isSupported) return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: 'var(--bg-card)' }}>
      <button onClick={() => setMuted(!muted)} className="p-1 rounded transition-colors" style={{ color: muted ? 'var(--text-dim)' : 'var(--accent)' }} title={muted ? '取消静音' : '静音'}>
        {muted ? (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
          </svg>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072M17.95 6.05a8 8 0 010 11.9M6.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L6.586 15z" />
          </svg>
        )}
      </button>
      {isSpeaking && (
        <span className="flex gap-0.5">
          {[1, 2, 3, 4].map((i) => (
            <span key={i} className="w-0.5 rounded animate-bounce" style={{ background: 'var(--accent)', height: `${8 + i * 4}px`, animationDelay: `${i * 0.1}s` }} />
          ))}
        </span>
      )}
      <select value={rate} onChange={(e) => setRate(Number(e.target.value))} className="bg-transparent text-xs border-none outline-none cursor-pointer text-[var(--text-dim)]">
        <option value={0.75}>0.75x</option><option value={1}>1x</option><option value={1.25}>1.25x</option>
      </select>
    </div>
  );
}
