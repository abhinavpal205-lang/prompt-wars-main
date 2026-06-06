import { useRef, useState } from 'react';
import { api, ApiError } from '../api/client';
import { MediaCaptor } from '../lib/capture';
import { useVoiceSession } from '../hooks/useVoiceSession';
import type { CheckinResult } from '../types';
import styles from './VoiceCheckin.module.css';

interface VoiceCheckinProps {
  onResult: (result: CheckinResult) => void;
  onUseForm: () => void;
}

const STATUS_TEXT: Record<string, string> = {
  idle: 'Ready when you are.',
  connecting: 'Connecting…',
  live: 'Live — Sahaay is listening.',
  ended: 'Conversation ended.',
  error: 'Voice is unavailable.',
};

/** ~1 minute supportive voice conversation with live captions. */
export function VoiceCheckin({ onResult, onUseForm }: VoiceCheckinProps) {
  const { status, captions, error, connect, end, transcript } = useVoiceSession();
  const [withCamera, setWithCamera] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const captorRef = useRef<MediaCaptor | null>(null);

  const start = () => {
    const captor = new MediaCaptor();
    captorRef.current = captor;
    void captor.start(withCamera).catch(() => undefined);
    void connect();
  };

  const finish = () => {
    end();
    const captured = captorRef.current?.stop() ?? { audioB64: null, frames: [] };
    captorRef.current = null;
    setSubmitting(true);
    setSubmitError(null);
    api
      .voiceCheckin({
        transcript,
        audio_segment_b64: captured.audioB64,
        frames_b64: captured.frames,
      })
      .then(onResult)
      .catch((err: unknown) => {
        setSubmitError(
          err instanceof ApiError ? err.message : 'Something went wrong. Please try again.',
        );
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <section aria-labelledby="voice-heading">
      <h1 id="voice-heading">Talk it out</h1>
      <p className={styles.lead}>
        A gentle one-minute conversation about how the last few days have felt.
      </p>
      <p className={styles.privacy}>
        <strong>We don&apos;t store your audio or video.</strong> A short sound snippet and a few
        camera frames (only if you allow the camera) are analyzed once for soft cues, then
        discarded.
      </p>

      {status === 'idle' && (
        <div className={styles.startBlock}>
          <label className={styles.cameraToggle}>
            <input
              type="checkbox"
              checked={withCamera}
              onChange={(event) => {
                setWithCamera(event.target.checked);
              }}
            />
            <span>Also use my camera for soft visual cues (optional)</span>
          </label>
          <button type="button" className={styles.primary} onClick={start}>
            Start the conversation
          </button>
        </div>
      )}

      <p role="status" className={styles.status}>
        {STATUS_TEXT[status]}
        {status === 'live' && (
          <span className={styles.indicators}>
            {' '}
            · 🎙️ mic on{withCamera ? ' · 📷 camera on' : ' · 📷 camera off'}
          </span>
        )}
      </p>

      {error && (
        <div className={styles.errorBlock}>
          <p role="alert">{error}</p>
          <button type="button" className={styles.secondary} onClick={onUseForm}>
            Use the quick form instead
          </button>
        </div>
      )}

      <div className={styles.captions} role="log" aria-live="polite" aria-label="Live captions">
        {captions.length === 0 && status === 'live' && (
          <p className={styles.captionHint}>Captions appear here as you talk.</p>
        )}
        {captions.map((line) => (
          <p key={line.id} className={line.speaker === 'You' ? styles.you : styles.sahaay}>
            <strong>{line.speaker}:</strong> {line.text}
          </p>
        ))}
      </div>

      {status === 'live' && (
        <button type="button" className={styles.primary} onClick={finish} disabled={submitting}>
          {submitting ? 'Reflecting…' : "I'm done — reflect"}
        </button>
      )}
      {status === 'ended' && submitting && <p role="status">Reflecting on your check-in…</p>}
      {submitError && <p role="alert">{submitError}</p>}
    </section>
  );
}
