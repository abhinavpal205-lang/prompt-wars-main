import { useId, useState } from 'react';
import { api, ApiError } from '../api/client';
import type { CheckinResult } from '../types';
import styles from './FormCheckin.module.css';

/**
 * Item texts pair with the backend's scoring semantics
 * (backend/app/constants.py): indexes 3, 5, 7, 9 are positively worded
 * and reverse-scored server-side.
 */
export const FORM_ITEMS: readonly string[] = [
  'I felt overwhelmed by my study load.',
  'I had trouble sleeping, or woke up tired.',
  'I felt anxious about results or rank.',
  'I was able to take breaks and relax a little.',
  'I felt I was falling behind compared to others.',
  'I felt on top of my syllabus and plan.',
  'I felt irritable or on edge.',
  'I enjoyed at least one thing outside studying.',
  'I felt pressure from family or teachers.',
  'I felt hopeful about the weeks ahead.',
];

export const LIKERT_LABELS: readonly string[] = [
  'Never',
  'Rarely',
  'Sometimes',
  'Often',
  'Very often',
];

const SAFETY_TEXT =
  'In the last week, did you have thoughts of hurting yourself, or feel that life isn’t worth living?';

interface FormCheckinProps {
  onResult: (result: CheckinResult) => void;
}

/** The private, accessibility-first check-in path: 10 Likert items + safety item. */
export function FormCheckin({ onResult }: FormCheckinProps) {
  const [answers, setAnswers] = useState<(number | null)[]>(() => FORM_ITEMS.map(() => null));
  const [safety, setSafety] = useState<boolean | null>(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const errorId = useId();

  const setAnswer = (index: number, value: number) => {
    setAnswers((current) => current.map((a, i) => (i === index ? value : a)));
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (answers.some((a) => a === null) || safety === null) {
      setError(
        'Please answer every question — including the last one. There are no wrong answers.',
      );
      return;
    }
    setError(null);
    setSubmitting(true);
    api
      .formCheckin({
        answers: answers.map((a) => a ?? 0),
        safety_flag: safety,
        free_note: note.trim() ? note.trim() : null,
      })
      .then(onResult)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
      })
      .finally(() => {
        setSubmitting(false);
      });
  };

  return (
    <section aria-labelledby="form-heading">
      <h1 id="form-heading">Quick check-in</h1>
      <p className={styles.lead}>
        Thinking about the <strong>last week</strong>, how often did each of these feel true? This
        stays on your device and your own dashboard only.
      </p>
      <form onSubmit={handleSubmit} noValidate>
        {FORM_ITEMS.map((item, index) => (
          <fieldset key={item} className={styles.item}>
            <legend className={styles.legend}>{`${index + 1}. ${item}`}</legend>
            <div className={styles.options} role="presentation">
              {LIKERT_LABELS.map((label, value) => (
                <label key={label} className={styles.option}>
                  <input
                    type="radio"
                    name={`item-${index}`}
                    value={value}
                    checked={answers[index] === value}
                    onChange={() => {
                      setAnswer(index, value);
                    }}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </fieldset>
        ))}

        <fieldset className={`${styles.item} ${styles.safety}`}>
          <legend className={styles.legend}>{SAFETY_TEXT}</legend>
          <p className={styles.safetyNote}>
            However you answer, you&apos;re not alone — if it&apos;s yes, we&apos;ll show you
            support options right away.
          </p>
          <div className={styles.options} role="presentation">
            <label className={styles.option}>
              <input
                type="radio"
                name="safety"
                checked={safety === false}
                onChange={() => {
                  setSafety(false);
                }}
              />
              <span>No</span>
            </label>
            <label className={styles.option}>
              <input
                type="radio"
                name="safety"
                checked={safety === true}
                onChange={() => {
                  setSafety(true);
                }}
              />
              <span>Yes</span>
            </label>
          </div>
        </fieldset>

        <div className={styles.noteBlock}>
          <label htmlFor="free-note">Anything else on your mind? (optional)</label>
          <textarea
            id="free-note"
            value={note}
            maxLength={2000}
            rows={3}
            onChange={(event) => {
              setNote(event.target.value);
            }}
            placeholder="Whatever you want to put down — it's kept encrypted."
          />
        </div>

        <div aria-live="polite">
          {error && (
            <p id={errorId} className={styles.error} role="alert">
              {error}
            </p>
          )}
        </div>

        <button
          type="submit"
          className={styles.submit}
          disabled={submitting}
          aria-describedby={error ? errorId : undefined}
        >
          {submitting ? 'Reflecting…' : 'Finish check-in'}
        </button>
      </form>
    </section>
  );
}
