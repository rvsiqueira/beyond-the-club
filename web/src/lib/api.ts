'use client';

import type {
  LoginRequest,
  RegisterRequest,
  CreateBookingRequest,
  MemberPreferences,
  StartMonitorRequest,
  SessionSearchRequest,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

// Auth error handler for token expiration
let authErrorHandler: (() => void) | null = null;

class ApiClient {
  private token: string | null = null;

  constructor() {
    // Load token from localStorage on client side
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
  }

  setAuthErrorHandler(handler: () => void) {
    authErrorHandler = handler;
  }

  getToken(): string | null {
    return this.token;
  }

  private setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', token);
    }
  }

  private clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      // Handle auth errors (401, 403)
      if (response.status === 401 || response.status === 403) {
        this.clearToken();
        if (authErrorHandler) {
          authErrorHandler();
        }
      }

      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  // Auth methods
  async login(data: LoginRequest): Promise<{ access_token: string }> {
    const result = await this.request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(result.access_token);
    return result;
  }

  async register(data: RegisterRequest): Promise<{ access_token: string }> {
    const result = await this.request<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(result.access_token);
    return result;
  }

  async getMe(): Promise<{ id: string; phone: string; name?: string }> {
    return this.request('/auth/me');
  }

  logout() {
    this.clearToken();
  }

  // Beyond Token methods
  async checkBeyondToken(): Promise<{ valid: boolean; phone?: string; expires_at?: number }> {
    return this.request('/auth/beyond/status');
  }

  async sendSmsCode(phone: string): Promise<{ message: string }> {
    return this.request('/auth/beyond/send-sms', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    });
  }

  async verifySmsCode(phone: string, code: string): Promise<{ success: boolean }> {
    return this.request('/auth/beyond/verify-sms', {
      method: 'POST',
      body: JSON.stringify({ phone, code }),
    });
  }

  // Members methods
  async getMembers(sport: string): Promise<{ members: any[]; total: number }> {
    return this.request(`/members?sport=${sport}`);
  }

  async getMember(id: number, sport: string): Promise<any> {
    return this.request(`/members/${id}?sport=${sport}`);
  }

  async getMemberPreferences(id: number, sport: string): Promise<MemberPreferences | null> {
    return this.request(`/members/${id}/preferences?sport=${sport}`);
  }

  async updateMemberPreferences(
    id: number,
    preferences: Partial<MemberPreferences>,
    sport: string
  ): Promise<MemberPreferences> {
    return this.request(`/members/${id}/preferences?sport=${sport}`, {
      method: 'PUT',
      body: JSON.stringify(preferences),
    });
  }

  async deleteMemberPreferences(id: number, sport: string): Promise<void> {
    return this.request(`/members/${id}/preferences?sport=${sport}`, {
      method: 'DELETE',
    });
  }

  // Availability methods
  async getAvailability(sport: string): Promise<any> {
    return this.request(`/availability?sport=${sport}`);
  }

  async scanAvailability(sport: string): Promise<any> {
    return this.request(`/availability/scan?sport=${sport}`, {
      method: 'POST',
    });
  }

  async getAvailableDates(sport: string, level?: string, waveSide?: string): Promise<any> {
    const params = new URLSearchParams({ sport });
    if (level) params.append('level', level);
    if (waveSide) params.append('wave_side', waveSide);
    return this.request(`/availability/dates?${params}`);
  }

  // Bookings methods
  async getBookings(sport: string, activeOnly: boolean = true): Promise<{ bookings: any[]; total: number }> {
    return this.request(`/bookings?sport=${sport}&active_only=${activeOnly}`);
  }

  async getBooking(voucherCode: string, sport: string): Promise<any> {
    return this.request(`/bookings/${voucherCode}?sport=${sport}`);
  }

  async createBooking(data: CreateBookingRequest, sport: string): Promise<any> {
    return this.request(`/bookings?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async cancelBooking(voucherCode: string, sport: string): Promise<void> {
    return this.request(`/bookings/${voucherCode}?sport=${sport}`, {
      method: 'DELETE',
    });
  }

  async swapBooking(voucherCode: string, newMemberId: number, sport: string): Promise<any> {
    return this.request(`/bookings/${voucherCode}/swap?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify({ new_member_id: newMemberId }),
    });
  }

  // Monitor methods
  async startMonitor(data: StartMonitorRequest, sport: string): Promise<{ monitor_id: string }> {
    return this.request(`/monitor/start?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMonitorStatus(monitorId: string): Promise<any> {
    return this.request(`/monitor/${monitorId}/status`);
  }

  async stopMonitor(monitorId: string): Promise<void> {
    return this.request(`/monitor/${monitorId}/stop`, {
      method: 'POST',
    });
  }

  async listMonitors(): Promise<{ monitors: any[]; total: number }> {
    return this.request('/monitor');
  }

  // Session search methods
  async getSessionOptions(): Promise<{
    levels: string[];
    wave_sides: string[];
    hours_by_level: Record<string, string[]>;
  }> {
    return this.request('/monitor/session-options');
  }

  async startSessionSearch(data: SessionSearchRequest, sport: string): Promise<{
    monitor_id: string;
    status: string;
    message: string;
    member_id: number;
    member_name: string;
    session: {
      level: string;
      wave_side: string;
      date: string;
      hour: string;
    };
  }> {
    return this.request(`/monitor/search-session?sport=${sport}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // WebSocket connections
  connectMonitorWs(monitorId: string, onMessage: (data: any) => void): WebSocket {
    const wsBase = API_BASE.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/monitor/ws/${monitorId}`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    return ws;
  }

  connectSessionSearchWs(monitorId: string, onMessage: (data: any) => void): WebSocket {
    const wsBase = API_BASE.replace(/^http/, 'ws');
    const ws = new WebSocket(`${wsBase}/monitor/ws/${monitorId}/session`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    return ws;
  }
}

export const api = new ApiClient();
