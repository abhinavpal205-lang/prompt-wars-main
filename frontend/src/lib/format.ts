/** Pure formatting and small chart helpers (unit-tested). */

import type { Band } from '../types';

export const BAND_META: Record<Band, { label: string; icon: string; className: string }> = {
  calm: { label: 'Steady', icon: '🌿', className: 'bandCalm' },
  mild: { label: 'A little pressed', icon: '🌤️', className: 'bandMild' },
  elevated: { label: 'Carrying a lot', icon: '🌧️', className: 'bandElevated' },
  high: { label: 'Really heavy', icon: '⛈️', className: 'bandHigh' },
};

/** Human date like "6 Jun, 4:30 pm" in the viewer's locale. */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Build an SVG polyline `points` string for a 0-100 series.
 * Y is inverted (SVG origin is top-left); a single point centers horizontally.
 */
export function trendPoints(
  values: number[],
  width: number,
  height: number,
  padding = 4,
): string {
  if (values.length === 0) return '';
  const innerW = width - padding * 2;
  const innerH = height - padding * 2;
  const step = values.length > 1 ? innerW / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = values.length > 1 ? padding + index * step : width / 2;
      const y = padding + innerH * (1 - clamp01(value / 100));
      return `${round1(x)},${round1(y)}`;
    })
    .join(' ');
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

/** Percent label for a 0-1 confidence, e.g. 0.35 -> "35%". */
export function confidencePercent(confidence: number): string {
  return `${Math.round(clamp01(confidence) * 100)}%`;
}
