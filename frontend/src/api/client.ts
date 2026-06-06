/** Typed fetch wrappers for the Sahaay API. */

import type {
  CheckinResult,
  DeletionResult,
  FormResponse,
  ProfileOut,
  ProfileUpdate,
  RealtimeTokenResponse,
  SentNotificationOut,
  TrendsResponse,
  VoiceCheckinRequest,
} from '../types';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string };
  detail?: unknown;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!response.ok) {
    let code = 'request_failed';
    let message = 'Something went wrong. Please try again.';
    try {
      const body = (await response.json()) as ErrorBody;
      if (body.error?.code) code = body.error.code;
      if (body.error?.message) message = body.error.message;
      else if (response.status === 422) message = 'Please check your answers and try again.';
    } catch {
      // non-JSON error body: keep the generic message
    }
    throw new ApiError(message, code, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  getProfile: (): Promise<ProfileOut> => request('/api/profile'),
  putProfile: (profile: ProfileUpdate): Promise<ProfileOut> =>
    request('/api/profile', { method: 'PUT', body: JSON.stringify(profile) }),
  getNotifications: (): Promise<SentNotificationOut[]> => request('/api/profile/notifications'),
  formCheckin: (payload: FormResponse): Promise<CheckinResult> =>
    request('/api/checkin/form', { method: 'POST', body: JSON.stringify(payload) }),
  voiceCheckin: (payload: VoiceCheckinRequest): Promise<CheckinResult> =>
    request('/api/checkin/voice', { method: 'POST', body: JSON.stringify(payload) }),
  mintRealtimeToken: (): Promise<RealtimeTokenResponse> =>
    request('/api/realtime/token', { method: 'POST' }),
  getTrends: (): Promise<TrendsResponse> => request('/api/history/trends'),
  deleteAllData: (): Promise<DeletionResult> => request('/api/history', { method: 'DELETE' }),
};
