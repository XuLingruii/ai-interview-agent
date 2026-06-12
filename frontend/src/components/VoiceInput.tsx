import { useRef } from 'react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition';

interface Props { onTranscript: (text: string) => void; }

export default function VoiceInput({ onTranscript }: Props) {
  const { isListening, isSupported, start, stop, getTranscript } = useSpeechRecognition();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  if (!isSupported) return null;

  const handleClick = () => {
    if (isListening) {
      stop();
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        const t = getTranscript().trim();
        if (t) onTranscript(t);
      }, 50);
    } else {
      if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
      start();
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="p-2 rounded-xl transition-all select-none"
      style={{
        background: isListening ? 'var(--red-bg)' : 'var(--bg-card)',
        color: isListening ? 'var(--red)' : 'var(--text-muted)',
        transform: isListening ? 'scale(1.1)' : '',
      }}
      title={isListening ? '点击停止识别' : '点击开始语音输入'}
    >
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 10v2a7 7 0 01-14 0v-2" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 19v3M8 22h8" />
      </svg>
      {isListening && <span className="block text-[10px] mt-0.5">录音中</span>}
    </button>
  );
}
