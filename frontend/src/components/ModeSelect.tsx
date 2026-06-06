import styles from './ModeSelect.module.css';

interface ModeSelectProps {
  onVoice: () => void;
  onForm: () => void;
}

/**
 * Two equally-prominent check-in modes. The form is a first-class path for
 * anyone in a public place, without a mic, or who prefers not to speak.
 */
export function ModeSelect({ onVoice, onForm }: ModeSelectProps) {
  return (
    <section aria-labelledby="mode-heading">
      <h1 id="mode-heading">How would you like to check in today?</h1>
      <p className={styles.lead}>Two minutes for yourself. Both ways are equally good.</p>
      <div className={styles.grid}>
        <button type="button" className={styles.card} onClick={onVoice}>
          <span aria-hidden="true" className={styles.icon}>
            🎙️
          </span>
          <span className={styles.title}>Talk it out</span>
          <span className={styles.desc}>
            A gentle voice conversation, about a minute. Nothing you say is recorded or stored.
          </span>
        </button>
        <button type="button" className={styles.card} onClick={onForm}>
          <span aria-hidden="true" className={styles.icon}>
            📝
          </span>
          <span className={styles.title}>Quick form</span>
          <span className={styles.desc}>
            Ten quiet questions. Completely private — no mic, no camera. Great for class or a
            library.
          </span>
        </button>
      </div>
    </section>
  );
}
