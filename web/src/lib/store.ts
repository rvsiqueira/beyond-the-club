import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';
import type { ToastData } from '@/components/ui/Toast';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  sport: string;
  setUser: (user: User | null) => void;
  setSport: (sport: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      sport: 'surf',
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      setSport: (sport) => set({ sport }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ sport: state.sport }),
    }
  )
);

interface UIState {
  sidebarOpen: boolean;
  mobileMenuOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleMobileMenu: () => void;
  setMobileMenuOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  mobileMenuOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleMobileMenu: () => set((state) => ({ mobileMenuOpen: !state.mobileMenuOpen })),
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
}));

// Monitor types
export interface MonitorMessage {
  type: string;
  message: string;
  level: string;
}

export interface MonitorResult {
  success: boolean;
  voucher?: string;
  access_code?: string;
  slot?: {
    date: string;
    interval: string;
    level: string;
    wave_side: string;
  };
  error?: string;
  member_name?: string;
}

export interface MonitorInfo {
  monitor_id: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'error' | 'stopped' | 'stopping';
  member_id: number;
  member_name: string;
  level: string;
  wave_side?: string;
  target_date: string;
  target_hour?: string;
  duration_minutes: number;
  elapsed_seconds: number;
  started_at?: number;
  messages: MonitorMessage[];
  result?: MonitorResult;
}

interface MonitorState {
  monitors: Record<string, MonitorInfo>;
  expandedMonitorId: string | null;
  setMonitor: (id: string, info: MonitorInfo) => void;
  updateMonitor: (id: string, partial: Partial<MonitorInfo>) => void;
  removeMonitor: (id: string) => void;
  setExpanded: (id: string | null) => void;
  clearCompleted: () => void;
  syncFromServer: (serverMonitors: MonitorInfo[]) => void;
}

export const useMonitorStore = create<MonitorState>()(
  persist(
    (set) => ({
      monitors: {},
      expandedMonitorId: null,
      setMonitor: (id, info) =>
        set((state) => ({
          monitors: { ...state.monitors, [id]: info },
        })),
      updateMonitor: (id, partial) =>
        set((state) => ({
          monitors: {
            ...state.monitors,
            [id]: state.monitors[id] ? { ...state.monitors[id], ...partial } : state.monitors[id],
          },
        })),
      removeMonitor: (id) =>
        set((state) => {
          const { [id]: _, ...rest } = state.monitors;
          return { monitors: rest };
        }),
      setExpanded: (id) => set({ expandedMonitorId: id }),
      clearCompleted: () =>
        set((state) => ({
          monitors: Object.fromEntries(
            Object.entries(state.monitors).filter(
              ([_, m]) => m.status === 'pending' || m.status === 'running'
            )
          ),
        })),
      syncFromServer: (serverMonitors) =>
        set((state) => {
          const newMonitors: Record<string, MonitorInfo> = {};
          // Only keep monitors that exist on the server
          for (const m of serverMonitors) {
            newMonitors[m.monitor_id] = m;
          }
          // Keep local pending monitors only if they were created very recently (< 30s)
          // This allows new monitors to appear before the server knows about them
          const now = Date.now() / 1000;
          for (const [id, monitor] of Object.entries(state.monitors)) {
            if (
              monitor.status === 'pending' &&
              !newMonitors[id] &&
              monitor.started_at &&
              now - monitor.started_at < 30
            ) {
              newMonitors[id] = monitor;
            }
          }
          return { monitors: newMonitors };
        }),
    }),
    {
      name: 'monitor-storage',
      partialize: (state) => ({ monitors: state.monitors }),
    }
  )
);

// Toast store
interface ToastState {
  toasts: ToastData[];
  addToast: (toast: Omit<ToastData, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: `toast-${Date.now()}-${Math.random().toString(36).slice(2)}` }],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
  clearToasts: () => set({ toasts: [] }),
}));
