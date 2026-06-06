import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CheckinResult } from '../types';
import { FormCheckin, FORM_ITEMS } from './FormCheckin';

const RESULT: CheckinResult = {
  band: 'calm',
  composite_0_100: 5,
  supportive_message: 'Steady days.',
  likely_triggers: [],
  coping_suggestions: ['Walk', 'Water', 'Rest'],
  crisis: false,
  crisis_resources: null,
  signals: [],
  disclaimer: 'not a diagnosis',
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('FormCheckin', () => {
  it('renders all ten items plus the safety item as labelled radio groups', () => {
    render(<FormCheckin onResult={vi.fn()} />);
    expect(screen.getAllByRole('group')).toHaveLength(FORM_ITEMS.length + 1);
    expect(screen.getAllByRole('radio').length).toBe(FORM_ITEMS.length * 5 + 2);
  });

  it('blocks submission until every question is answered', async () => {
    render(<FormCheckin onResult={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /Finish check-in/ }));
    expect(screen.getByRole('alert')).toHaveTextContent(/answer every question/i);
  });

  it('submits answers and reports the result', async () => {
    const onResult = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(RESULT), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    render(<FormCheckin onResult={onResult} />);
    for (const radio of screen.getAllByRole('radio', { name: 'Never' })) {
      await userEvent.click(radio);
    }
    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
    await userEvent.click(screen.getByRole('button', { name: /Finish check-in/ }));

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/checkin/form',
      expect.objectContaining({ method: 'POST' }),
    );
    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const payload = JSON.parse(requestInit.body as string) as {
      answers: number[];
      safety_flag: boolean;
    };
    expect(payload.answers).toEqual(Array<number>(10).fill(0));
    expect(payload.safety_flag).toBe(false);
    await vi.waitFor(() => {
      expect(onResult).toHaveBeenCalledWith(RESULT);
    });
  });
});
