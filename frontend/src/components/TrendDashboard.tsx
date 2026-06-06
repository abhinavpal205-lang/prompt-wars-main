import { useState } from 'react';
import { useCheckins } from '../hooks/useCheckins';
import { BAND_META, formatDate, trendPoints } from '../lib/format';
import styles from './TrendDashboard.module.css';

const CHART_WIDTH = 320;
const CHART_HEIGHT = 120;

interface TrendDashboardProps {
  onCheckin: () => void;
}

/** Mood/stress over time, recurring triggers, transparency, and data control. */
export function TrendDashboard({ onCheckin }: TrendDashboardProps) {
  const { trends, notifications, loading, error, deleteAll } = useCheckins();
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);

  const handleDelete = () => {
    const sure = window.confirm(
      'Delete ALL your Sahaay data — check-ins, notes, profile, and notification history? This cannot be undone.',
    );
    if (!sure) return;
    setDeleting(true);
    deleteAll()
      .then(() => {
        setDeleted(true);
      })
      .catch(() => undefined)
      .finally(() => {
        setDeleting(false);
      });
  };

  if (loading) return <p role="status">Loading your history…</p>;
  if (error) return <p role="alert">{error}</p>;

  const points = trends?.points ?? [];
  const values = points.map((p) => p.composite_0_100);

  return (
    <section aria-labelledby="dash-heading">
      <h1 id="dash-heading">Your wellbeing over time</h1>

      {points.length === 0 ? (
        <div className={styles.empty}>
          <p>
            {deleted
              ? 'All your data has been deleted.'
              : 'No check-ins yet — your trend will appear here.'}
          </p>
          <button type="button" className="btnPrimary" onClick={onCheckin}>
            Do a check-in
          </button>
        </div>
      ) : (
        <>
          <figure className={styles.chartCard}>
            <figcaption>
              Pressure level across your last {points.length} check-in
              {points.length > 1 ? 's' : ''} (lower is lighter)
            </figcaption>
            <svg
              viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
              role="img"
              aria-label={`Trend of ${points.length} check-ins, most recent is ${
                BAND_META[points[points.length - 1]?.band ?? 'mild'].label
              }`}
              className={styles.chart}
            >
              <line
                x1="0"
                y1={CHART_HEIGHT / 2}
                x2={CHART_WIDTH}
                y2={CHART_HEIGHT / 2}
                className={styles.midline}
              />
              <polyline points={trendPoints(values, CHART_WIDTH, CHART_HEIGHT)} />
            </svg>
          </figure>

          {(trends?.recurring_triggers.length ?? 0) > 0 && (
            <>
              <h2>Keeps coming up</h2>
              <ul className={styles.chips}>
                {trends?.recurring_triggers.map((trigger) => (
                  <li key={trigger}>{trigger}</li>
                ))}
              </ul>
            </>
          )}

          <h2>Past check-ins</h2>
          <ul className={styles.history}>
            {[...points].reverse().map((point) => {
              const meta = BAND_META[point.band];
              return (
                <li key={point.id}>
                  <span className={styles.when}>{formatDate(point.created_at)}</span>
                  <span>
                    <span aria-hidden="true">{meta.icon}</span> {meta.label}
                  </span>
                  <span className={styles.mode}>{point.mode === 'voice' ? 'voice' : 'form'}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}

      <h2>What we sent your parent/guardian</h2>
      {notifications.length === 0 ? (
        <p className={styles.muted}>
          Nothing has been sent. Updates go out only if you turn them on in Settings, and every
          message appears here word for word.
        </p>
      ) : (
        <ul className={styles.notifications}>
          {notifications.map((notification) => (
            <li key={`${notification.created_at}-${notification.subject}`}>
              <details>
                <summary>
                  {formatDate(notification.created_at)} — {notification.subject} (to{' '}
                  {notification.recipient})
                </summary>
                <pre className={styles.body}>{notification.body}</pre>
              </details>
            </li>
          ))}
        </ul>
      )}

      <h2>Your data, your call</h2>
      <p className={styles.muted}>
        Sahaay keeps only coarse check-in summaries and your encrypted note — never audio, video, or
        transcripts.
      </p>
      <button type="button" className="btnDanger" onClick={handleDelete} disabled={deleting}>
        {deleting ? 'Deleting…' : 'Delete all my data'}
      </button>
    </section>
  );
}
