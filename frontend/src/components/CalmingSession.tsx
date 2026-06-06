import { useEffect, useRef, useState } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { useVoiceSession } from '../hooks/useVoiceSession';
import type { Band } from '../types';
import styles from './CalmingSession.module.css';

export const CALMING_SECONDS = 60;

// Client-side escalation guard: mirrors the backend's crisis keywords.
const CRISIS_HINTS = ['suicide', 'kill myself', 'end my life', 'hurt myself', 'want to die'];

interface CalmingSessionProps {
  band: Band;
  triggers: string[];
  onDone: () => void;
  onCrisis: () => void;
}

/**
 * An optional ~1-minute grounding companion after a non-crisis check-in.
 * Hard-capped client-side at 60s (the token's 70s TTL is the server backstop).
 * Nothing said here is stored.
 */
export function CalmingSession({ band, triggers, onDone, onCrisis }: CalmingSessionProps) {
  const { status, captions, error, connect, end } = useVoiceSession({
    profile: 'calming',
    band,
    triggers,
  });
  const [finished, setFinished] = useState(false);
  const endedRef = useRef(false);

  const finish = () => {
    if (endedRef.current) return;
    endedRef.current = true;
    end();
    setFinished(true);
  };

  const remaining = useCountdown(status === 'live', CALMING_SECONDS, finish);

  useEffect(() => {
    void connect();
  }, [connect]);

  // Mid-session escalation: stop calming and surface real help at once.
  useEffect(() => {
    const spoken = captions.map((line) => line.text.toLowerCase()).join(' ');
    if (CRISIS_HINTS.some((hint) => spoken.includes(hint))) {
      endedRef.current = true;
      end();
      onCrisis();
    }
  }, [captions, end, onCrisis]);

  if (finished) {
    return (
      <section aria-labelledby="calming-heading">
        <h1 id="calming-heading">That&apos;s your minute</h1>
        <p>Hope that helped — be kind to yourself today.</p>
        <button type="button" className="btnPrimary" onClick={onDone}>
          Back to your reflection
        </button>
      </section>
    );
  }

  return (
    <section aria-labelledby="calming-heading">
      <h1 id="calming-heading">A calming minute</h1>
      <p className={styles.privacy}>
        <strong>We don&apos;t store this conversation.</strong> One minute of grounding, then
        you&apos;re back.
      </p>

      {error ? (
        <div>
          <p role="alert">{error}</p>
          <button type="button" className="btnPrimary" onClick={onDone}>
            Back to your reflection
          </button>
        </div>
      ) : (
        <>
          <p role="status" className={styles.status}>
            {status === 'live'
              ? 'Live — take a slow breath.'
              : status === 'connecting'
                ? 'Connecting…'
                : 'Ready.'}
          </p>
          {status === 'live' && (
            <p className={styles.timer} role="timer" aria-label="Time remaining">
              0:{String(remaining).padStart(2, '0')} left
            </p>
          )}
          <div className={styles.captions} role="log" aria-live="polite" aria-label="Live captions">
            {captions.map((line) => (
              <p key={line.id}>
                <strong>{line.speaker}:</strong> {line.text}
              </p>
            ))}
          </div>
          <button type="button" className="btnPrimary" onClick={finish}>
            End now
          </button>
        </>
      )}
    </section>
  );
}
