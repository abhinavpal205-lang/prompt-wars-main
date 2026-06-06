import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import { CrisisScreen } from './CrisisScreen';
import { Disclaimer } from './Disclaimer';
import { FormCheckin } from './FormCheckin';
import { ModeSelect } from './ModeSelect';

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
