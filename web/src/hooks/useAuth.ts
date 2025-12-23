'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { LoginRequest, RegisterRequest } from '@/types';

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, setUser, logout: storeLogout } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = api.getToken();
      if (token && !user) {
        try {
          const userData = await api.getMe();
          setUser(userData);
        } catch {
          api.logout();
          storeLogout();
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, [user, setUser, storeLogout]);

  const login = async (data: LoginRequest) => {
    setError(null);
    setIsLoading(true);
    try {
      await api.login(data);
      const userData = await api.getMe();
      setUser(userData);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    setError(null);
    setIsLoading(true);
    try {
      await api.register(data);
      const userData = await api.getMe();
      setUser(userData);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.logout();
    storeLogout();
    router.push('/login');
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
  };
}
