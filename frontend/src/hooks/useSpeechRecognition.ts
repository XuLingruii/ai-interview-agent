import { useState, useRef, useCallback, useEffect } from 'react';

interface SpeechRecognitionHook {
  isListening: boolean;
  isSupported: boolean;
  transcript: string;
  start: () => void;
  stop: () => void;
  getTranscript: () => string;
}

export function useSpeechRecognition(): SpeechRecognitionHook {
  const [isListening, setIsListening] = useState(false);
  const [isSupported] = useState(() => {
    try {
      return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    } catch {
      return false;
    }
  });
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const transcriptRef = useRef('');

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    try {
      const recognition = new SpeechRecognition();
      recognition.lang = 'zh-CN';
      recognition.interimResults = true;
      recognition.continuous = false;

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        try {
          let final = '';
          let interim = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const r = event.results[i];
            if (!r || !r.length) continue;
            if (r.isFinal) {
              final += r[0].transcript;
            } else {
              interim += r[0].transcript;
            }
          }
          const t = final || interim;
          transcriptRef.current = t;
          setTranscript(t);
        } catch {
          // ignore parse errors
        }
      };

      recognition.onerror = (e) => {
        if ((e as SpeechRecognitionErrorEvent).error === 'no-speech') {
          transcriptRef.current = '';
          setTranscript('');
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } catch {
      // browser doesn't support or init failed
    }
    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch { /* ignore */ }
      }
    };
  }, []);

  const start = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      setTranscript('');
      transcriptRef.current = '';
      recognitionRef.current.start();
      setIsListening(true);
    } catch (e: any) {
      // If recognition was aborted (e.g. by StrictMode cleanup), it's unusable — re-create
      if (e?.message?.includes('aborted') || e?.name === 'InvalidStateError') {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
          const rec = new SpeechRecognition();
          rec.lang = 'zh-CN';
          rec.interimResults = true;
          rec.continuous = false;
          rec.onresult = recognitionRef.current!.onresult;
          rec.onerror = recognitionRef.current!.onerror;
          rec.onend = recognitionRef.current!.onend;
          recognitionRef.current = rec;
          try { rec.start(); setIsListening(true); } catch { /* still failed */ }
        }
      }
      // permission denied or already running — silently ignore
    }
  }, []);

  const stop = useCallback(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
      setIsListening(false);
    } catch {
      // already stopped
    }
  }, []);

  const getTranscript = useCallback(() => transcriptRef.current, []);

  return { isListening, isSupported, transcript, start, stop, getTranscript };
}
