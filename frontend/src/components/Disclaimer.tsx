import styles from './Disclaimer.module.css';

const TEXT =
  'Sahaay is a self-reflection companion, not a medical or diagnostic tool. ' +
  'It cannot assess, label or treat mental health. If you are struggling, ' +
  'please talk to someone you trust or call Tele-MANAS: 14416 (free, 24x7).';

interface DisclaimerProps {
  variant: 'footer' | 'callout';
}

/** The persistent non-clinical disclaimer, shown in the footer and on results. */
export function Disclaimer({ variant }: DisclaimerProps) {
  if (variant === 'callout') {
    return <p className={styles.callout}>{TEXT}</p>;
  }
  return <p className={styles.footer}>{TEXT}</p>;
}
