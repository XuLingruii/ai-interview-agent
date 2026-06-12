import { useLayoutEffect, useEffect, useRef, useCallback } from 'react';

type SSECallback = (event: string, data: unknown) => void;

export function useSSE(sessionId: string | null, onEvent: SSECallback) {
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const onEventRef = useRef(onEvent);
  useLayoutEffect(() => { onEventRef.current = onEvent; });

  const disconnect = useCallback(() => {
    abortRef.current?.abort();
    readerRef.current?.cancel();
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const controller = new AbortController();
    abortRef.current = controller;

    fetch(`/api/interview/chat?sessionId=${sessionId}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok || !res.body) return;
        const reader = res.body.getReader();
        readerRef.current = reader;
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          let eventType = '';
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              const data = line.slice(6);
              try {
                const parsed = JSON.parse(data);
                onEventRef.current(eventType, parsed);
              } catch {
                // ignore parse errors
              }
              eventType = '';
            }
          }
        }
      })
      .catch(() => {
        // connection closed or aborted
      });

    return () => {
      controller.abort();
    };
  }, [sessionId]);

  return { disconnect };
}
