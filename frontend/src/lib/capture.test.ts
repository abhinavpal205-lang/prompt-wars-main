import { describe, expect, it } from 'vitest';
import {
  arrayBufferToBase64,
  downsample,
  encodeWavPcm16,
  floatTo16BitPcm,
  trailingSegment,
} from './capture';

describe('floatTo16BitPcm', () => {
  it('maps the float range to 16-bit integers and clamps overflow', () => {
    const pcm = floatTo16BitPcm(new Float32Array([0, 1, -1, 2, -2]));
    expect(Array.from(pcm)).toEqual([0, 32767, -32768, 32767, -32768]);
  });
});

describe('downsample', () => {
  it('reduces sample count by the rate ratio, preserving values', () => {
    const input = new Float32Array(48).fill(0.5);
    const output = downsample(input, 48_000, 16_000);
    expect(output.length).toBe(16);
    for (const value of output) expect(value).toBeCloseTo(0.5);
  });

  it('returns input untouched when no reduction is needed', () => {
    const input = new Float32Array([0.1, 0.2]);
    expect(downsample(input, 16_000, 16_000)).toBe(input);
  });
});

describe('encodeWavPcm16', () => {
  it('produces a valid mono 16-bit WAV header', () => {
    const samples = new Float32Array(100).fill(0.25);
    const buffer = encodeWavPcm16(samples, 16_000);
    const view = new DataView(buffer);
    const ascii = (offset: number, length: number) =>
      String.fromCharCode(...new Uint8Array(buffer, offset, length));

    expect(buffer.byteLength).toBe(44 + 200);
    expect(ascii(0, 4)).toBe('RIFF');
    expect(ascii(8, 4)).toBe('WAVE');
    expect(view.getUint16(22, true)).toBe(1); // mono
    expect(view.getUint32(24, true)).toBe(16_000); // sample rate
    expect(view.getUint16(34, true)).toBe(16); // bit depth
    expect(view.getUint32(40, true)).toBe(200); // data bytes
  });
});

describe('arrayBufferToBase64', () => {
  it('encodes bytes as base64', () => {
    expect(arrayBufferToBase64(new Uint8Array([72, 105]).buffer)).toBe('SGk=');
  });
});

describe('trailingSegment', () => {
  it('keeps only the most recent samples across chunk boundaries', () => {
    const chunks = [new Float32Array([1, 2, 3, 4, 5]), new Float32Array([6, 7, 8, 9, 10])];
    const segment = trailingSegment(chunks, 1, 7); // 7 samples at 1 Hz
    expect(Array.from(segment)).toEqual([4, 5, 6, 7, 8, 9, 10]);
  });

  it('returns everything when the buffer is shorter than the window', () => {
    const segment = trailingSegment([new Float32Array([1, 2])], 16_000, 8);
    expect(Array.from(segment)).toEqual([1, 2]);
  });
});
