// User & Auth
export interface User {
  id: string;
  phone: string;
  name?: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export interface RegisterRequest {
  phone: string;
  password: string;
  name?: string;
}

// Members
export interface Member {
  member_id: number;
  name: string;
  social_name: string;
  is_titular: boolean;
  has_booking: boolean;
  has_active_booking?: boolean;
  has_preferences: boolean;
  usage: number;
  limit: number;
}

export interface SessionPreference {
  level: string;
  wave_side: string;
  priority: number;
}

export interface MemberPreferences {
  member_id: number;
  sport: string;
  sessions: SessionPreference[];
  target_hours: string[];
  target_dates: string[];
}

// Availability
export interface AvailableSlot {
  date: string;
  interval: string;
  level: string;
  wave_side: string;
  available: number;
  max_quantity: number;
  package_id: string;
  product_id: string;
}

export interface AvailabilityResponse {
  slots: AvailableSlot[];
  sport: string;
  total: number;
  from_cache: boolean;
  cache_valid: boolean;
  cache_updated_at?: string;
}

// Bookings
export interface Booking {
  voucher_code: string;
  access_code: string;
  member_id: number;
  member_name: string;
  date: string;
  interval: string;
  level?: string;
  wave_side?: string;
  status: string;
}

export interface BookingsListResponse {
  bookings: Booking[];
  sport: string;
  total: number;
}

export interface CreateBookingRequest {
  member_id: number;
  date: string;
  interval: string;
  level?: string;
  wave_side?: string;
  court?: string;
  package_id: string;
  product_id: string;
}

// Monitor
export interface MonitorStatus {
  monitor_id: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'stopping';
  member_ids: number[];
  target_dates?: string[];
  duration_minutes: number;
  elapsed_seconds: number;
  results: Record<number, MonitorResult>;
}

export interface MonitorResult {
  success: boolean;
  voucher?: string;
  access_code?: string;
  slot?: AvailableSlot;
  error?: string;
}

export interface StartMonitorRequest {
  member_ids: number[];
  target_dates?: string[];
  duration_minutes?: number;
  check_interval_seconds?: number;
}

// Sports
export interface SportConfig {
  name: string;
  levels: string[];
  wave_sides?: string[];
  courts?: string[];
}

// API Response
export interface ApiError {
  detail: string;
}
