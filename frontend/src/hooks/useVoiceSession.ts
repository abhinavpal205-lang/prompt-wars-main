import { RealtimeAgent, RealtimeSession } from '@openai/agents-realtime';
import type { RealtimeItem } from '@openai/agents-realtime';
import { useCallback, useRef, useState } from 'react';
import { api, ApiError } from '../api/client';

export type VoiceStatus = 'idle' | 'connecting' | 'live' | 'ended' | 'error';

export interface CaptionLine {
  id: string;
  speaker: 'You' | 'Sahaay';
  text: string;
}

function partText(part: unknown): string {
  if (typeof part !== 'object' || part === null) return '';
  const record = part as Record<string, unknown>;
  if (typeof record.text === 'string') return record.text;
  if (typeof record.transcript === 'string') return record.transcript;
  return '';
}

/** Extract readable caption lines from the realtime conversation history. */
export function toCaptions(history: RealtimeItem[]): CaptionLine[] {
  const lines: CaptionLine[] = [];
  for (const item of history) {
    if (item.type !== 'message' || item.role === 'system') continue;
    const parts: unknown[] = item.content;
    const text = parts.map(partText).join(' ').trim();
    if (text) {
      lines.push({ id: item.itemId, speaker: item.role === 'user' ? 'You' : 'Sahaay', text });
    }
  }
  return lines;
}

/**
 * Manages the realtime voice conversation: token fetch, WebRTC connect,
 * live captions, and a clean transcript for the check-in submission.
 * The instructions and model are pinned server-side in the minted secret.
 */
export function useVoiceSession() {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [captions, setCaptions] = useState<CaptionLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef<RealtimeSession | null>(null);

  const connect = useCallback(async () => {
    setStatus('connecting');
    setError(null);
    try {
      const token = await api.mintRealtimeToken();
      const agent = new RealtimeAgent({ name: 'Sahaay' });
      const session = new RealtimeSession(agent, { model: token.model });
      session.on('history_updated', (history) => {
        setCaptions(toCaptions(history));
      });
      await session.connect({ apiKey: token.value });
      sessionRef.current = session;
      setStatus('live');
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 503
          ? 'Voice check-in is unavailable right now — the quick form works just as well.'
          : 'Could not start the voice session. You can use the quick form instead.',
      );
      setStatus('error');
    }
  }, []);

  const end = useCallback(() => {
    sessionRef.current?.close();
    sessionRef.current = null;
    setStatus('ended');
  }, []);

  const transcript = captions.map((line) => `${line.speaker}: ${line.text}`).join('\n');

  return { status, captions, error, connect, end, transcript };
}
