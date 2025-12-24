'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  phone: string;
  name?: string;
}

interface AuthState {
  user: User | null;
  sport: string;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setSport: (sport: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      sport: 'surf',
      isAuthenticated: false,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
        }),

      setSport: (sport) => set({ sport }),

      logout: () =>
        set({
          user: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        sport: state.sport,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
