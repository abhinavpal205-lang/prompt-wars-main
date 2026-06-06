import { describe, expect, it } from 'vitest';
import { BAND_META, clamp01, confidencePercent, formatDate, trendPoints } from './format';

describe('formatDate', () => {
  it('formats an ISO date into a short human string', () => {
    const formatted = formatDate('2026-06-06T10:00:00Z');
    expect(formatted).toContain('6');
    expect(formatted).not.toContain('T10:00');
  });

  it('returns the input when unparseable', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date');
  });
});

describe('trendPoints', () => {
  it('returns empty string for no data', () => {
    expect(trendPoints([], 320, 120)).toBe('');
  });

  it('centers a single point horizontally', () => {
    const points = trendPoints([50], 320, 120);
    expect(points.startsWith('160,')).toBe(true);
  });

  it('inverts the y axis: higher strain is higher up', () => {
    const [low, high] = trendPoints([0, 100], 100, 100, 4).split(' ');
    expect(low).toBe('4,96');
    expect(high).toBe('96,4');
  });

  it('spaces points evenly across the width', () => {
    const xs = trendPoints([10, 20, 30], 104, 100, 2)
      .split(' ')
      .map((pair) => Number(pair.split(',')[0]));
    expect(xs).toEqual([2, 52, 102]);
  });
});

describe('clamp01 / confidencePercent', () => {
  it('clamps out-of-range values', () => {
    expect(clamp01(-1)).toBe(0);
    expect(clamp01(2)).toBe(1);
    expect(clamp01(0.4)).toBe(0.4);
  });

  it('renders confidence as a percent', () => {
    expect(confidencePercent(0.35)).toBe('35%');
    expect(confidencePercent(1.7)).toBe('100%');
  });
});

describe('BAND_META', () => {
  it('always pairs color with text and icon (never color alone)', () => {
    for (const meta of Object.values(BAND_META)) {
      expect(meta.label.length).toBeGreaterThan(0);
      expect(meta.icon.length).toBeGreaterThan(0);
    }
  });
});
