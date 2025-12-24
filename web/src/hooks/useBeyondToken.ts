'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface BeyondTokenStatus {
  valid: boolean;
  phone?: string;
  expires_at?: number;
}

export function useBeyondTokenStatus() {
  return useQuery<BeyondTokenStatus>({
    queryKey: ['beyond-token-status'],
    queryFn: () => api.checkBeyondToken(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Check every minute
  });
}
