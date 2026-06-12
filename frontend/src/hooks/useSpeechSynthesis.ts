import { useCallback, useState, useEffect } from 'react';

interface SpeechSynthesisHook {
  speak: (text: string) => void;
  stop: () => void;
  isSpeaking: boolean;
  isSupported: boolean;
  muted: boolean;
  setMuted: (m: boolean) => void;
  rate: number;
  setRate: (r: number) => void;
  voiceIndex: number;
  setVoiceIndex: (i: number) => void;
  voices: SpeechSynthesisVoice[];
}

export function useSpeechSynthesis(): SpeechSynthesisHook {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported] = useState(() => {
    return typeof window !== 'undefined' && !!window.speechSynthesis;
  });
  const [muted, setMuted] = useState(false);
  const [rate, setRate] = useState(1);
  const [voiceIndex, setVoiceIndex] = useState(0);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      const loadVoices = () => {
        const v = window.speechSynthesis.getVoices().filter((v) => v.lang.startsWith('zh'));
        setVoices(v.length ? v : window.speechSynthesis.getVoices());
      };
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  const speak = useCallback(
    (text: string) => {
      if (!window.speechSynthesis || muted) return;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'zh-CN';
      utterance.rate = rate;
      if (voices[voiceIndex]) {
        utterance.voice = voices[voiceIndex];
      }
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    },
    [muted, rate, voiceIndex, voices]
  );

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, []);

  return { speak, stop, isSpeaking, isSupported, muted, setMuted, rate, setRate, voiceIndex, setVoiceIndex, voices };
}
