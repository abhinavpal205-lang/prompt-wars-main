/**
 * Client-side capture of a short audio segment and a few sampled frames.
 *
 * Privacy: only the small payloads produced here ever leave the browser; the
 * backend extracts coarse signals and discards them. Nothing is recorded to
 * disk and nothing is persisted. Pure encoding helpers are unit-tested.
 */

export const SEGMENT_SECONDS = 8;
export const TARGET_SAMPLE_RATE = 16_000;
export const MAX_FRAMES = 5;
export const FRAME_INTERVAL_MS = 12_000;
const FRAME_WIDTH = 320;
const JPEG_QUALITY = 0.6;

export interface CaptureResult {
  audioB64: string | null;
  frames: string[];
}

/** Convert [-1, 1] float samples to 16-bit PCM. */
export function floatTo16BitPcm(samples: Float32Array): Int16Array {
  const out = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[i] ?? 0));
    out[i] = Math.round(clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff);
  }
  return out;
}

/** Naive averaging downsampler (mono). Returns input if no reduction needed. */
export function downsample(input: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (toRate >= fromRate || input.length === 0) return input;
  const ratio = fromRate / toRate;
  const length = Math.floor(input.length / ratio);
  const out = new Float32Array(length);
  for (let i = 0; i < length; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0;
    for (let j = start; j < end; j += 1) sum += input[j] ?? 0;
    out[i] = end > start ? sum / (end - start) : 0;
  }
  return out;
}

/** Encode mono float samples as a 16-bit PCM WAV file. */
export function encodeWavPcm16(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const pcm = floatTo16BitPcm(samples);
  const dataLength = pcm.length * 2;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);
  writeAscii(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeAscii(view, 8, 'WAVE');
  writeAscii(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeAscii(view, 36, 'data');
  view.setUint32(40, dataLength, true);
  for (let i = 0; i < pcm.length; i += 1) {
    view.setInt16(44 + i * 2, pcm[i] ?? 0, true);
  }
  return buffer;
}

function writeAscii(view: DataView, offset: number, text: string): void {
  for (let i = 0; i < text.length; i += 1) {
    view.setUint8(offset + i, text.charCodeAt(i));
  }
}

export function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

/** Keep only the trailing `seconds` of audio from a chunk list. */
export function trailingSegment(
  chunks: Float32Array[],
  sampleRate: number,
  seconds: number,
): Float32Array {
  const maxSamples = sampleRate * seconds;
  const total = chunks.reduce((sum, c) => sum + c.length, 0);
  const keep = Math.min(total, maxSamples);
  const out = new Float32Array(keep);
  let writeIndex = keep;
  for (let i = chunks.length - 1; i >= 0 && writeIndex > 0; i -= 1) {
    const chunkData = chunks[i];
    if (!chunkData) continue;
    const take = Math.min(chunkData.length, writeIndex);
    out.set(chunkData.subarray(chunkData.length - take), writeIndex - take);
    writeIndex -= take;
  }
  return out;
}

/**
 * Live captor: keeps a rolling audio buffer (mic) and samples webcam frames.
 * Both inputs are optional; failures simply mean fewer signals.
 */
export class MediaCaptor {
  private chunks: Float32Array[] = [];
  private bufferedSamples = 0;
  private frames: string[] = [];
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private video: HTMLVideoElement | null = null;
  private frameTimer: number | null = null;

  /** True when a camera track is live (for the UI indicator). */
  cameraActive = false;
  /** True when a mic track is live (for the UI indicator). */
  micActive = false;

  async start(withCamera: boolean): Promise<void> {
    this.stream = await this.openStream(withCamera);
    if (!this.stream) return;
    this.micActive = this.stream.getAudioTracks().length > 0;
    if (this.micActive) this.startAudio(this.stream);
    if (withCamera && this.stream.getVideoTracks().length > 0) {
      this.cameraActive = true;
      this.startFrames(this.stream);
    }
  }

  /** Stop everything and return the captured payloads. */
  stop(): CaptureResult {
    let audioB64: string | null = null;
    if (this.audioContext && this.bufferedSamples > 0) {
      const recent = trailingSegment(this.chunks, this.audioContext.sampleRate, SEGMENT_SECONDS);
      const mono = downsample(recent, this.audioContext.sampleRate, TARGET_SAMPLE_RATE);
      audioB64 = arrayBufferToBase64(encodeWavPcm16(mono, TARGET_SAMPLE_RATE));
    }
    this.teardown();
    return { audioB64, frames: [...this.frames] };
  }

  private async openStream(withCamera: boolean): Promise<MediaStream | null> {
    try {
      return await navigator.mediaDevices.getUserMedia({ audio: true, video: withCamera });
    } catch {
      if (!withCamera) return null;
      try {
        return await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        return null;
      }
    }
  }

  private startAudio(stream: MediaStream): void {
    this.audioContext = new AudioContext();
    this.source = this.audioContext.createMediaStreamSource(stream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    const maxBuffered = this.audioContext.sampleRate * (SEGMENT_SECONDS + 2);
    this.processor.onaudioprocess = (event) => {
      this.chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      this.bufferedSamples += event.inputBuffer.length;
      while (this.bufferedSamples > maxBuffered && this.chunks.length > 1) {
        const dropped = this.chunks.shift();
        this.bufferedSamples -= dropped?.length ?? 0;
      }
    };
    this.source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  private startFrames(stream: MediaStream): void {
    this.video = document.createElement('video');
    this.video.muted = true;
    this.video.playsInline = true;
    this.video.srcObject = stream;
    void this.video.play().catch(() => undefined);
    const grab = () => {
      if (!this.video || this.frames.length >= MAX_FRAMES) return;
      const { videoWidth, videoHeight } = this.video;
      if (!videoWidth || !videoHeight) return;
      const canvas = document.createElement('canvas');
      canvas.width = FRAME_WIDTH;
      canvas.height = Math.round((videoHeight / videoWidth) * FRAME_WIDTH);
      const context = canvas.getContext('2d');
      if (!context) return;
      context.drawImage(this.video, 0, 0, canvas.width, canvas.height);
      this.frames.push(canvas.toDataURL('image/jpeg', JPEG_QUALITY));
    };
    this.frameTimer = window.setInterval(grab, FRAME_INTERVAL_MS);
    window.setTimeout(grab, 1500); // first frame early, once video warms up
  }

  private teardown(): void {
    if (this.frameTimer !== null) window.clearInterval(this.frameTimer);
    this.processor?.disconnect();
    this.source?.disconnect();
    void this.audioContext?.close().catch(() => undefined);
    this.stream?.getTracks().forEach((track) => {
      track.stop();
    });
    this.video = null;
    this.micActive = false;
    this.cameraActive = false;
  }
}
