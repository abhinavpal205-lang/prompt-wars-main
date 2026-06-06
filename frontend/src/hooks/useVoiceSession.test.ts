import type { RealtimeItem } from '@openai/agents-realtime';
import { describe, expect, it } from 'vitest';
import { toCaptions } from './useVoiceSession';

const history = [
  {
    itemId: 'u1',
    type: 'message',
    role: 'user',
    status: 'completed',
    content: [{ type: 'input_audio', transcript: 'I am a bit tired', audio: null }],
  },
  {
    itemId: 'a1',
    type: 'message',
    role: 'assistant',
    status: 'completed',
    content: [{ type: 'output_text', text: 'Thanks for sharing that.' }],
  },
  {
    itemId: 's1',
    type: 'message',
    role: 'system',
    content: [{ type: 'input_text', text: 'internal' }],
  },
  {
    itemId: 'e1',
    type: 'message',
    role: 'user',
    status: 'completed',
    content: [{ type: 'input_audio', transcript: null, audio: null }],
  },
] as unknown as RealtimeItem[];

describe('toCaptions', () => {
  it('extracts speaker-labelled lines from user and assistant messages', () => {
    expect(toCaptions(history)).toEqual([
      { id: 'u1', speaker: 'You', text: 'I am a bit tired' },
      { id: 'a1', speaker: 'Sahaay', text: 'Thanks for sharing that.' },
    ]);
  });

  it('skips system messages and empty transcripts', () => {
    const lines = toCaptions(history);
    expect(lines.find((line) => line.id === 's1')).toBeUndefined();
    expect(lines.find((line) => line.id === 'e1')).toBeUndefined();
  });
});
