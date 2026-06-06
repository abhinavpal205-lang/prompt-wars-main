import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { CheckinResult } from '../types';
import { ResultCard } from './ResultCard';

const RESULT: CheckinResult = {
  band: 'elevated',
  composite_0_100: 62.5,
  supportive_message: 'It sounds like the last few days have felt heavy.',
  likely_triggers: ['sleep', 'results pressure'],
  coping_suggestions: ['Take a 10-minute reset', 'Protect your sleep tonight', 'Tell a friend'],
  crisis: false,
  crisis_resources: null,
  signals: [
    {
      modality: 'form',
      distress_0_100: 62.5,
      confidence_0_1: 1,
      notes: 'self-report form (primary signal)',
      crisis_flag: false,
      triggers: ['sleep'],
    },
    {
      modality: 'audio',
      distress_0_100: 0,
      confidence_0_1: 0,
      notes: 'no audio segment provided',
      crisis_flag: false,
      triggers: [],
    },
  ],
  disclaimer: 'Sahaay is a self-reflection companion, not a medical or diagnostic tool.',
};

describe('ResultCard', () => {
  it('shows the band as text (never color alone), message, triggers, and tips', () => {
    render(<ResultCard result={RESULT} onDone={vi.fn()} />);
    expect(screen.getByText(/Carrying a lot/)).toBeInTheDocument();
    expect(screen.getByText(RESULT.supportive_message)).toBeInTheDocument();
    expect(screen.getByText('sleep')).toBeInTheDocument();
    expect(screen.getByText('Protect your sleep tonight')).toBeInTheDocument();
  });

  it('discloses which signals were used and which were dropped', () => {
    render(<ResultCard result={RESULT} onDone={vi.fn()} />);
    expect(screen.getByText(/Signals we considered/)).toBeInTheDocument();
    expect(screen.getByText(/not used — no audio segment provided/)).toBeInTheDocument();
  });

  it('always renders the non-clinical disclaimer', () => {
    render(<ResultCard result={RESULT} onDone={vi.fn()} />);
    expect(screen.getByText(/not a medical or diagnostic tool/)).toBeInTheDocument();
  });

  it('calls onDone', async () => {
    const onDone = vi.fn();
    render(<ResultCard result={RESULT} onDone={onDone} />);
    await userEvent.click(screen.getByRole('button', { name: 'Done' }));
    expect(onDone).toHaveBeenCalledTimes(1);
  });
});
