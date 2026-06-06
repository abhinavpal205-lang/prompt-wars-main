import { useState } from 'react';
import { api, ApiError } from '../api/client';
import type { Cadence, ProfileOut } from '../types';
import styles from './ParentSettings.module.css';

interface ParentSettingsProps {
  profile: ProfileOut;
  intro?: boolean;
  onSaved: (profile: ProfileOut) => void;
}

const CADENCES: { value: Cadence; label: string; description: string }[] = [
  {
    value: 'weekly',
    label: 'Weekly summary',
    description: 'At most one gentle update a week about how you seem to be doing.',
  },
  {
    value: 'on_elevated',
    label: 'Only on heavier days',
    description: 'A supportive note only when a check-in suggests you are carrying a lot.',
  },
  {
    value: 'off',
    label: 'Paused',
    description: 'Keep your contact saved, but send nothing.',
  },
];

/**
 * Profile + consent. Sharing is the student's choice, can be changed any
 * time, and every message sent is visible on the dashboard — no surveillance.
 */
export function ParentSettings({ profile, intro = false, onSaved }: ParentSettingsProps) {
  const [name, setName] = useState(profile.name);
  const [exam, setExam] = useState(profile.exam);
  const [parentName, setParentName] = useState(profile.consent.parent_name ?? '');
  const [parentEmail, setParentEmail] = useState(profile.consent.parent_email ?? '');
  const [notifyEnabled, setNotifyEnabled] = useState(profile.consent.notify_enabled);
  const [cadence, setCadence] = useState<Cadence>(profile.consent.cadence);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError('Please tell us what to call you.');
      return;
    }
    if (notifyEnabled && !parentEmail.trim()) {
      setError('Add a parent/guardian email, or turn sharing off.');
      return;
    }
    setError(null);
    setSaving(true);
    api
      .putProfile({
        name: name.trim(),
        exam: exam.trim(),
        consent: {
          parent_name: parentName.trim() || null,
          parent_email: parentEmail.trim() || null,
          notify_enabled: notifyEnabled,
          cadence,
          student_visible: true,
        },
      })
      .then(onSaved)
      .catch((err: unknown) => {
        setError(
          err instanceof ApiError && err.status === 422
            ? 'That email address doesn’t look right — please check it.'
            : 'Could not save right now. Please try again.',
        );
      })
      .finally(() => {
        setSaving(false);
      });
  };

  return (
    <section aria-labelledby="settings-heading">
      <h1 id="settings-heading">{intro ? 'Welcome to Sahaay' : 'Your settings'}</h1>
      {intro && (
        <p className={styles.lead}>
          A couple of quick things, then you&apos;re in. Only your name is needed — everything else
          is optional and always changeable.
        </p>
      )}
      <form onSubmit={handleSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor="student-name">What should we call you?</label>
          <input
            id="student-name"
            type="text"
            value={name}
            maxLength={120}
            onChange={(event) => {
              setName(event.target.value);
            }}
            autoComplete="given-name"
          />
        </div>
        <div className={styles.field}>
          <label htmlFor="exam">Which exam are you preparing for? (optional)</label>
          <input
            id="exam"
            type="text"
            value={exam}
            maxLength={60}
            placeholder="NEET, JEE, boards…"
            onChange={(event) => {
              setExam(event.target.value);
            }}
          />
        </div>

        <fieldset className={styles.consent}>
          <legend>Sharing with a parent/guardian (your choice)</legend>
          <p className={styles.consentNote}>
            If you turn this on, Sahaay sends supportive updates — how you seem to be doing and ways
            they can help. <strong>Never scores, never your answers or words.</strong> You can read
            every message we send on your dashboard, and switch this off any time.
          </p>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={notifyEnabled}
              onChange={(event) => {
                setNotifyEnabled(event.target.checked);
              }}
            />
            <span>Share supportive updates with my parent/guardian</span>
          </label>

          {notifyEnabled && (
            <>
              <div className={styles.field}>
                <label htmlFor="parent-name">Their name (optional)</label>
                <input
                  id="parent-name"
                  type="text"
                  value={parentName}
                  maxLength={120}
                  onChange={(event) => {
                    setParentName(event.target.value);
                  }}
                />
              </div>
              <div className={styles.field}>
                <label htmlFor="parent-email">Their email</label>
                <input
                  id="parent-email"
                  type="email"
                  value={parentEmail}
                  onChange={(event) => {
                    setParentEmail(event.target.value);
                  }}
                />
              </div>
              <fieldset className={styles.cadence}>
                <legend>How often?</legend>
                {CADENCES.map((option) => (
                  <label key={option.value} className={styles.cadenceOption}>
                    <input
                      type="radio"
                      name="cadence"
                      checked={cadence === option.value}
                      onChange={() => {
                        setCadence(option.value);
                      }}
                    />
                    <span>
                      <strong>{option.label}</strong> — {option.description}
                    </span>
                  </label>
                ))}
              </fieldset>
            </>
          )}
        </fieldset>

        <div aria-live="polite">
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
        </div>
        <button type="submit" className={styles.save} disabled={saving}>
          {saving ? 'Saving…' : intro ? "Let's begin" : 'Save settings'}
        </button>
      </form>
    </section>
  );
}
