import { BAND_META, confidencePercent } from '../lib/format';
import type { CheckinResult } from '../types';
import { Disclaimer } from './Disclaimer';
import styles from './ResultCard.module.css';

const MODALITY_LABEL: Record<string, string> = {
  form: 'Your answers (primary)',
  transcript: 'What you talked about',
  audio: 'How you sounded (soft hint)',
  facial: 'Camera frames (soft hint)',
};

interface ResultCardProps {
  result: CheckinResult;
  onDone: () => void;
  onCalm?: () => void;
}

/** A gentle, transparent reflection of the check-in (never a diagnosis). */
export function ResultCard({ result, onDone, onCalm }: ResultCardProps) {
  const meta = BAND_META[result.band];
  return (
    <section aria-labelledby="result-heading" className={styles.card}>
      <h1 id="result-heading">Thanks for checking in</h1>
      <Disclaimer variant="callout" />
      <p className={`${styles.band} ${styles[meta.className] ?? ''}`}>
        <span aria-hidden="true">{meta.icon}</span> Right now: {meta.label}
      </p>
      <p className={styles.message}>{result.supportive_message}</p>

      {result.likely_triggers.length > 0 && (
        <>
          <h2>What seems to be on your mind</h2>
          <ul className={styles.triggers}>
            {result.likely_triggers.map((trigger) => (
              <li key={trigger}>{trigger}</li>
            ))}
          </ul>
        </>
      )}

      <h2>Small things that can help today</h2>
      <ul className={styles.tips}>
        {result.coping_suggestions.map((tip) => (
          <li key={tip}>{tip}</li>
        ))}
      </ul>

      <details className={styles.signals}>
        <summary>Signals we considered (full transparency)</summary>
        <ul>
          {result.signals.map((signal) => (
            <li key={signal.modality}>
              <strong>{MODALITY_LABEL[signal.modality] ?? signal.modality}:</strong>{' '}
              {signal.confidence_0_1 > 0
                ? `weight confidence ${confidencePercent(signal.confidence_0_1)} — ${signal.notes}`
                : `not used — ${signal.notes}`}
            </li>
          ))}
        </ul>
        <p className={styles.signalsNote}>
          Voice tone and camera cues are unreliable hints and can only nudge the result. What you
          tell us always matters most.
        </p>
      </details>

      <div className={styles.actions}>
        {/* Never offered for a crisis check-in — CrisisScreen takes over there. */}
        {!result.crisis && onCalm && (
          <button type="button" className={styles.calm} onClick={onCalm}>
            Take a calming minute
          </button>
        )}
        <button type="button" className={styles.done} onClick={onDone}>
          Done
        </button>
      </div>
    </section>
  );
}
