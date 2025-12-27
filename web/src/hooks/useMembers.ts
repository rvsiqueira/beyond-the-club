'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { MemberPreferences, Member } from '@/types';

export function useMembers() {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['members', sport],
    queryFn: () => api.getMembers(sport, false),
  });
}

export function useRefreshMembers() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: () => api.getMembers(sport, true),
    onSuccess: (data: { members: Member[]; total: number; from_cache: boolean }) => {
      // Update the members cache with fresh data
      queryClient.setQueryData(['members', sport], data);
    },
  });
}

export function useMember(id: number) {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['member', id, sport],
    queryFn: () => api.getMember(id, sport),
    enabled: !!id,
  });
}

export function useMemberPreferences(id: number) {
  const sport = useAuthStore((state) => state.sport);

  return useQuery({
    queryKey: ['member-preferences', id, sport],
    queryFn: () => api.getMemberPreferences(id, sport),
    enabled: !!id,
  });
}

export function useUpdatePreferences(id: number) {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: (preferences: Partial<MemberPreferences>) =>
      api.updateMemberPreferences(id, preferences, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['member-preferences', id] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
  });
}

export function useDeletePreferences(id: number) {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: () => api.deleteMemberPreferences(id, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['member-preferences', id] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
  });
}
