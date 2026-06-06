import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type { SentNotificationOut, TrendsResponse } from '../types';

/** Dashboard state: trends, parent notifications, and the data wipe. */
export function useCheckins() {
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [notifications, setNotifications] = useState<SentNotificationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [trendsData, sent] = await Promise.all([api.getTrends(), api.getNotifications()]);
      setTrends(trendsData);
      setNotifications(sent);
    } catch {
      setError('Could not load your history right now.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const deleteAll = useCallback(async () => {
    await api.deleteAllData();
    await refresh();
  }, [refresh]);

  return { trends, notifications, loading, error, refresh, deleteAll };
}
