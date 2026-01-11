import type {
  AuthTokens,
  LoginRequest,
  RegisterRequest,
  User,
  Member,
  MemberPreferences,
  AvailabilityResponse,
  BookingsListResponse,
  Booking,
  CreateBookingRequest,
  MonitorStatus,
  StartMonitorRequest,
  SessionSearchRequest,
  SessionOptionsResponse,
  SportConfig,
} from '@/types';

// API base URL - always use relative path (routed by nginx in production)
const API_BASE = '/api/v1';

// Custom error type for Beyond auth requirement
export interface BeyondAuthError extends Error {
  isBeyondAuthRequired: boolean;
}

export function isBeyondAuthError(error: unknown): error is BeyondAuthError {
  return error instanceof Error && (error as BeyondAuthError).isBeyondAuthRequired === true;
}

// Custom error type for invalid/expired token
export interface AuthTokenError extends Error {
  isAuthTokenError: boolean;
}

export function isAuthTokenError(error: unknown): error is AuthTokenError {
  return error instanceof Error && (error as AuthTokenError).isAuthTokenError === true;
}

class ApiClient {
  private token: string | null = null;
  private onAuthError: (() => void) | null = null;

  // Set callback for auth errors (called when token is invalid/expired)
  setAuthErrorHandler(handler: () => void) {
    this.onAuthError = handler;
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers as Record<string, string>),
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      const errorMessage = error.detail || `HTTP ${response.status}`;

      // Check for Beyond auth required header
      const beyondAuthRequired = response.headers.get('X-Beyond-Auth-Required');
      if (response.status === 401 && beyondAuthRequired === 'true') {
        const beyondError = new Error('Beyond verification required');
        (beyondError as BeyondAuthError).isBeyondAuthRequired = true;
        throw beyondError;
      }

      // Check for invalid/expired token errors
      if (response.status === 401 || response.status === 403) {
        const isTokenError =
          errorMessage.toLowerCase().includes('invalid') ||
          errorMessage.toLowerCase().includes('expired') ||
          errorMessage.toLowerCase().includes('token') ||
          errorMessage.toLowerCase().includes('not authenticated') ||
          errorMessage.toLowerCase().includes('could not validate');

        if (isTokenError) {
          // Clear token and trigger auth error handler
          this.setToken(null);
          if (this.onAuthError) {
            this.onAuthError();
          }
          const tokenError = new Error(errorMessage);
          (tokenError as AuthTokenError).isAuthTokenError = true;
          throw tokenError;
        }
      }

      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Auth
  async login(data: LoginRequest): Promise<AuthTokens> {
    const response = await this.fetch<{ tokens: AuthTokens }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(response.tokens.access_token);
    return response.tokens;
  }

  async register(data: RegisterRequest): Promise<AuthTokens> {
    const response = await this.fetch<{ tokens: AuthTokens }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(response.tokens.access_token);
    return response.tokens;
  }

  async loginByPhone(phone: string): Promise<AuthTokens> {
    const response = await this.fetch<{ tokens: AuthTokens }>('/auth/login/phone', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
    this.setToken(response.tokens.access_token);
    return response.tokens;
  }

  async refreshToken(): Promise<AuthTokens> {
    const tokens = await this.fetch<AuthTokens>('/auth/refresh', {
      method: 'POST',
    });
    this.setToken(tokens.access_token);
    return tokens;
  }

  async getMe(): Promise<User> {
    return this.fetch<User>('/auth/me');
  }

  logout() {
    this.setToken(null);
  }

  // Beyond API Authentication (SMS verification)
  async requestBeyondSMS(phone: string): Promise<{ session_info: string }> {
    return this.fetch('/auth/beyond/request-sms', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
  }

  async verifyBeyondSMS(phone: string, code: string, sessionInfo: string): Promise<{ success: boolean }> {
    return this.fetch('/auth/beyond/verify-sms', {
      method: 'POST',
      body: JSON.stringify({ phone, code, session_info: sessionInfo }),
    });
  }

  async checkBeyondToken(): Promise<{ valid: boolean; phone?: string }> {
    return this.fetch('/auth/beyond/status');
  }

  // Members
  async getMembers(sport: string = 'surf', refresh: boolean = false): Promise<{ members: Member[]; total: number; from_cache: boolean }> {
    return this.fetch(`/members?sport=${sport}&refresh=${refresh}`);
  }

  async getMember(id: number, sport: string = 'surf'): Promise<Member> {
    return this.fetch(`/members/${id}?sport=${sport}`);
  }

  async getMemberPreferences(id: number, sport: string = 'surf'): Promise<MemberPreferences> {
    return this.fetch(`/members/${id}/preferences?sport=${sport}`);
  }

  async updateMemberPreferences(
    id: number,
    preferences: Partial<MemberPreferences>,
    sport: string = 'surf'
  ): Promise<MemberPreferences> {
    return this.fetch(`/members/${id}/preferences?sport=${sport}`, {
      method: 'PUT',
      body: JSON.stringify(preferences),
    });
  }

  async deleteMemberPreferences(id: number, sport: string = 'surf'): Promise<void> {
    await this.fetch(`/members/${id}/preferences?sport=${sport}`, {
      method: 'DELETE',
    });
  }

  // Availability
  async getAvailability(sport: string = 'surf'): Promise<AvailabilityResponse> {
    return this.fetch(`/availability?sport=${sport}`);
  }

  async scanAvailability(sport: string = 'surf'): Promise<AvailabilityResponse> {
    return this.fetch(`/availability/scan?sport=${sport}`, {
      method: 'POST',
    });
  }

  async getAvailableDates(
    sport: string = 'surf',
    level?: string,
    waveSide?: string
  ): Promise<{ dates: string[] }> {
    const params = new URLSearchParams({ sport });
    if (level) params.set('level', level);
    if (waveSide) params.set('wave_side', waveSide);
    return this.fetch(`/availability/dates?${params}`);
  }

  // Bookings
  async getBookings(sport: string = 'surf', activeOnly: boolean = true): Promise<BookingsListResponse> {
    return this.fetch(`/bookings?sport=${sport}&active_only=${activeOnly}`);
  }

  async getBooking(voucherCode: string, sport: string = 'surf'): Promise<Booking> {
    return this.fetch(`/bookings/${voucherCode}?sport=${sport}`);
  }

  async createBooking(data: CreateBookingRequest, sport: string = 'surf'): Promise<Booking> {
    return this.fetch(`/bookings?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async cancelBooking(voucherCode: string, sport: string = 'surf'): Promise<void> {
    await this.fetch(`/bookings/${voucherCode}?sport=${sport}`, {
      method: 'DELETE',
    });
  }

  async swapBooking(
    voucherCode: string,
    newMemberId: number,
    sport: string = 'surf'
  ): Promise<{ new_voucher: string; new_access_code: string }> {
    return this.fetch(`/bookings/${voucherCode}/swap?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify({ new_member_id: newMemberId }),
    });
  }

  // Monitor
  async startMonitor(data: StartMonitorRequest, sport: string = 'surf'): Promise<{ monitor_id: string }> {
    return this.fetch(`/monitor/start?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMonitorStatus(monitorId: string): Promise<MonitorStatus> {
    return this.fetch(`/monitor/${monitorId}/status`);
  }

  async stopMonitor(monitorId: string): Promise<void> {
    await this.fetch(`/monitor/${monitorId}/stop`, {
      method: 'POST',
    });
  }

  async listMonitors(): Promise<{ monitors: Record<string, MonitorStatus>; total: number }> {
    return this.fetch('/monitor');
  }

  async getActiveMonitors(): Promise<{
    monitors: Array<{
      monitor_id: string;
      type: string;
      status: string;
      member_id: number;
      member_name: string;
      level: string;
      wave_side?: string;
      target_date: string;
      target_hour?: string;
      duration_minutes: number;
      elapsed_seconds: number;
      started_at?: number;
      messages: Array<{ type: string; message: string; level: string }>;
      result?: unknown;
    }>;
  }> {
    return this.fetch('/monitor/user/active');
  }

  async updateMonitor(
    monitorId: string,
    data: {
      level?: string;
      wave_side?: string;
      target_hour?: string;
      duration_minutes?: number;
    }
  ): Promise<{
    success: boolean;
    monitor_id: string;
    message: string;
    restarted: boolean;
    updated_fields: string[];
  }> {
    return this.fetch(`/monitor/${monitorId}/update`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  // Sports
  async getSports(): Promise<{ sports: Record<string, SportConfig> }> {
    return this.fetch('/sports');
  }

  async getSport(name: string): Promise<SportConfig> {
    return this.fetch(`/sports/${name}`);
  }

  // WebSocket for Monitor
  connectMonitorWs(monitorId: string, onMessage: (data: unknown) => void): WebSocket {
    // Build WebSocket URL based on current page location
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:3000';
    const ws = new WebSocket(`${protocol}//${host}${API_BASE}/monitor/ws/${monitorId}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        console.error('Failed to parse WebSocket message');
      }
    };

    return ws;
  }

  // Session Search
  async getSessionOptions(): Promise<SessionOptionsResponse> {
    return this.fetch('/monitor/session-options');
  }

  async startSessionSearch(
    data: SessionSearchRequest,
    sport: string = 'surf'
  ): Promise<{
    monitor_id: string;
    status: string;
    message: string;
    member_id: number;
    member_name: string;
    session: { level: string; wave_side: string; date: string; hour: string };
  }> {
    return this.fetch(`/monitor/search-session?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  connectSessionSearchWs(monitorId: string, onMessage: (data: unknown) => void): WebSocket {
    // Build WebSocket URL based on current page location
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost:3000';
    const ws = new WebSocket(`${protocol}//${host}${API_BASE}/monitor/ws/${monitorId}/session`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch {
        console.error('Failed to parse WebSocket message');
      }
    };

    return ws;
  }
}

export const api = new ApiClient();
