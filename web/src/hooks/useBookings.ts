'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { CreateBookingRequest } from '@/types';

export function useBookings(activeOnly: boolean = true) {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['bookings', sport, activeOnly],
    queryFn: () => api.getBookings(sport, activeOnly),
  });
}

export function useBooking(voucherCode: string) {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['booking', voucherCode, sport],
    queryFn: () => api.getBooking(voucherCode, sport),
    enabled: !!voucherCode,
  });
}

export function useCreateBooking() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: (data: CreateBookingRequest) => api.createBooking(data, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
      queryClient.invalidateQueries({ queryKey: ['member'] });
      queryClient.invalidateQueries({ queryKey: ['availability'] });
    },
  });
}

export function useCancelBooking() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: (voucherCode: string) => api.cancelBooking(voucherCode, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
      queryClient.invalidateQueries({ queryKey: ['member'] });
    },
  });
}

export function useSwapBooking() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: ({ voucherCode, newMemberId }: { voucherCode: string; newMemberId: number }) =>
      api.swapBooking(voucherCode, newMemberId, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bookings'] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
      queryClient.invalidateQueries({ queryKey: ['member'] });
    },
  });
}
