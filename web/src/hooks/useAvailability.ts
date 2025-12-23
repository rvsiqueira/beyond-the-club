'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

export function useAvailability() {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['availability', sport],
    queryFn: () => api.getAvailability(sport),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useScanAvailability() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: () => api.scanAvailability(sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
  });
}

export function useAvailableDates(level?: string, waveSide?: string) {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['available-dates', sport, level, waveSide],
    queryFn: () => api.getAvailableDates(sport, level, waveSide),
    enabled: !!level || !!waveSide,
  });
}
