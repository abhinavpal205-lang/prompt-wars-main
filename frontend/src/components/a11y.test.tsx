import { render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import type { CheckinResult, ProfileOut, TrendsResponse } from '../types';
import { CrisisScreen } from './CrisisScreen';
import { Disclaimer } from './Disclaimer';
import { FormCheckin } from './FormCheckin';
import { ModeSelect } from './ModeSelect';
import { ParentSettings } from './ParentSettings';
import { ResultCard } from './ResultCard';
import { TrendDashboard } from './TrendDashboard';
import { VoiceCheckin } from './VoiceCheckin';

const PROFILE: ProfileOut = {
  name: 'Ravi',
  exam: 'NEET',
  consent: {
    parent_name: null,
    parent_email: null,
    notify_enabled: false,
    cadence: 'weekly',
    student_visible: true,
  },
  onboarded: true,
};

const RESULT: CheckinResult = {
  band: 'mild',
  composite_0_100: 30,
  supportive_message: 'A bit of pressure in the mix.',
  likely_triggers: ['sleep'],
  coping_suggestions: ['Take a break', 'Drink water', 'Text a friend'],
  crisis: false,
  crisis_resources: null,
  signals: [],
  disclaimer: 'not a diagnosis',
};

const TRENDS: TrendsResponse = {
  points: [
    {
      id: 1,
      created_at: '2026-06-06T10:00:00Z',
      mode: 'form',
      band: 'mild',
      composite_0_100: 30,
      triggers: ['sleep'],
      crisis: false,
    },
  ],
  recurring_triggers: ['sleep'],
};

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('accessibility (axe)', () => {
  it('ModeSelect has no violations', async () => {
    const { container } = render(<ModeSelect onVoice={vi.fn()} onForm={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('FormCheckin has no violations', async () => {
    const { container } = render(<FormCheckin onResult={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('CrisisScreen has no violations and always shows Tele-MANAS numbers', async () => {
    const { container, getByText } = render(<CrisisScreen onBack={vi.fn()} />);
    expect(getByText('14416')).toBeInTheDocument();
    expect(getByText('1-800-891-4416')).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ResultCard has no violations', async () => {
    const { container } = render(<ResultCard result={RESULT} onDone={vi.fn()} onCalm={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('VoiceCheckin has no violations', async () => {
    const { container } = render(<VoiceCheckin onResult={vi.fn()} onUseForm={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ParentSettings (onboarding variant) has no violations', async () => {
    const { container } = render(<ParentSettings profile={PROFILE} intro onSaved={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('TrendDashboard with data has no violations', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: string) =>
        Promise.resolve(input.includes('/trends') ? jsonResponse(TRENDS) : jsonResponse([])),
      ),
    );
    const { container } = render(<TrendDashboard onCheckin={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText(/Past check-ins/)).toBeInTheDocument();
    });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('App shell has no violations, manages focus and titles on navigation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(jsonResponse(PROFILE))),
    );
    const { container } = render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/How would you like to check in/)).toBeInTheDocument();
    });
    expect(document.title).toBe('Check in — Sahaay');
    expect(await axe(container)).toHaveNoViolations();

    screen.getByRole('button', { name: /Quick form/ }).click();
    await waitFor(() => {
      expect(document.title).toBe('Quick form check-in — Sahaay');
    });
    expect(document.activeElement).toBe(screen.getByRole('main'));
  });

  it('Disclaimer renders in both variants', () => {
    const { getAllByText } = render(
      <>
        <Disclaimer variant="footer" />
        <Disclaimer variant="callout" />
      </>,
    );
    expect(getAllByText(/not a medical or diagnostic tool/)).toHaveLength(2);
  });
});
