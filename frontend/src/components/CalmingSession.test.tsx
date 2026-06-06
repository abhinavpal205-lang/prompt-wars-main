import { act, render, renderHook, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCountdown } from '../hooks/useCountdown';
import type { CheckinResult } from '../types';
import { CalmingSession } from './CalmingSession';
import { ResultCard } from './ResultCard';

const CRISIS_RESULT: CheckinResult = {
  band: 'high',
  composite_0_100: 80,
  supportive_message: 'msg',
  likely_triggers: [],
  coping_suggestions: ['a', 'b', 'c'],
  crisis: true,
  crisis_resources: { helpline_name: 'Tele-MANAS', phone_numbers: ['14416'], message: 'help' },
  signals: [],
  disclaimer: 'd',
};

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('auto-fires exactly once when the minute is up', () => {
    const onElapsed = vi.fn();
    const { result } = renderHook(() => useCountdown(true, 60, onElapsed));
    act(() => {
      vi.advanceTimersByTime(61_000);
    });
    expect(onElapsed).toHaveBeenCalledTimes(1);
    expect(result.current).toBe(0);
    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    expect(onElapsed).toHaveBeenCalledTimes(1);
  });

  it('does not tick while inactive', () => {
    const onElapsed = vi.fn();
    renderHook(() => useCountdown(false, 60, onElapsed));
    act(() => {
      vi.advanceTimersByTime(120_000);
    });
    expect(onElapsed).not.toHaveBeenCalled();
  });
});

describe('calming entry point', () => {
  it('is never offered on a crisis result', () => {
    render(<ResultCard result={CRISIS_RESULT} onDone={vi.fn()} onCalm={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /calming minute/i })).not.toBeInTheDocument();
  });

  it('is offered on a non-crisis result', () => {
    render(
      <ResultCard
        result={{ ...CRISIS_RESULT, crisis: false, crisis_resources: null }}
        onDone={vi.fn()}
        onCalm={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: /calming minute/i })).toBeInTheDocument();
  });
});

describe('CalmingSession', () => {
  it('shows the no-storage note and has no axe violations', async () => {
    const { container } = render(
      <CalmingSession band="mild" triggers={['sleep']} onDone={vi.fn()} onCrisis={vi.fn()} />,
    );
    expect(screen.getByText(/don't store this conversation/i)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});
