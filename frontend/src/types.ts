/** Types mirroring the backend schemas (backend/app/schemas.py). */

export type Band = 'calm' | 'mild' | 'elevated' | 'high';
export type Modality = 'form' | 'transcript' | 'audio' | 'facial';
export type Cadence = 'off' | 'weekly' | 'on_elevated';
export type CheckinMode = 'form' | 'voice';

export interface ConsentSettings {
  parent_name: string | null;
  parent_email: string | null;
  notify_enabled: boolean;
  cadence: Cadence;
  student_visible: boolean;
}

export interface ProfileUpdate {
  name: string;
  exam: string;
  consent: ConsentSettings;
}

export interface ProfileOut extends ProfileUpdate {
  onboarded: boolean;
}

export interface FormResponse {
  answers: number[];
  safety_flag: boolean;
  free_note: string | null;
}

export interface VoiceCheckinRequest {
  transcript: string;
  audio_segment_b64: string | null;
  frames_b64: string[];
}

export interface SignalResult {
  modality: Modality;
  distress_0_100: number;
  confidence_0_1: number;
  notes: string;
  crisis_flag: boolean;
  triggers: string[];
}

export interface CrisisResources {
  helpline_name: string;
  phone_numbers: string[];
  message: string;
}

export interface CheckinResult {
  band: Band;
  composite_0_100: number;
  supportive_message: string;
  likely_triggers: string[];
  coping_suggestions: string[];
  crisis: boolean;
  crisis_resources: CrisisResources | null;
  signals: SignalResult[];
  disclaimer: string;
}

export interface TrendPoint {
  id: number;
  created_at: string;
  mode: CheckinMode;
  band: Band;
  composite_0_100: number;
  triggers: string[];
  crisis: boolean;
}

export interface TrendsResponse {
  points: TrendPoint[];
  recurring_triggers: string[];
}

export interface SentNotificationOut {
  created_at: string;
  recipient: string;
  subject: string;
  body: string;
}

export interface DeletionResult {
  deleted_checkins: number;
  deleted_notifications: number;
}

export interface RealtimeTokenResponse {
  value: string;
  expires_at: number;
  model: string;
}
