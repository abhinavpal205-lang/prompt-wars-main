import type { CrisisResources } from '../types';
import styles from './CrisisScreen.module.css';

const DEFAULT_RESOURCES: CrisisResources = {
  helpline_name: 'Tele-MANAS — Government of India mental health helpline',
  phone_numbers: ['14416', '1-800-891-4416'],
  message:
    "You matter, and you don't have to carry this alone. Tele-MANAS is free, confidential and " +
    'available 24x7 in your language. Please also consider reaching out right now to someone ' +
    'you trust — a parent, a friend, a teacher.',
};

interface CrisisScreenProps {
  resources?: CrisisResources | null;
  onBack: () => void;
}

/** Calm, immediate help. Never gated behind scoring or network calls. */
export function CrisisScreen({ resources, onBack }: CrisisScreenProps) {
  const help = resources ?? DEFAULT_RESOURCES;
  return (
    <section aria-labelledby="crisis-heading" className={styles.wrap}>
      <h1 id="crisis-heading">You deserve support right now</h1>
      <p className={styles.message}>{help.message}</p>
      <div className={styles.helpline}>
        <h2>{help.helpline_name}</h2>
        <p className={styles.free}>Free · confidential · 24x7 · in your language</p>
        <ul className={styles.numbers}>
          {help.phone_numbers.map((number) => (
            <li key={number}>
              <a href={`tel:${number.replaceAll('-', '')}`}>{number}</a>
            </li>
          ))}
        </ul>
      </div>
      <p>
        If you can, tell someone near you how you&apos;re feeling — a parent, a sibling, a friend, a
        teacher. You don&apos;t have to find perfect words.
      </p>
      <button type="button" className={styles.back} onClick={onBack}>
        Back to Sahaay
      </button>
    </section>
  );
}
