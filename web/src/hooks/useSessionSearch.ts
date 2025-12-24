'use client';

import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { SessionSearchRequest, SessionOptionsResponse } from '@/types';

interface SessionSearchMessage {
  type: 'status' | 'started' | 'completed' | 'error';
  level?: string;
  message?: string;
  result?: Record<string, unknown>;
  elapsed_seconds?: number;
}

/**
 * Hook to fetch session options (levels, wave_sides, hours_by_level).
 */
export function useSessionOptions() {
  return useQuery<SessionOptionsResponse>({
    queryKey: ['session-options'],
    queryFn: () => api.getSessionOptions(),
    staleTime: 5 * 60 * 1000, // 5 minutes - options don't change often
  });
}

/**
 * Hook to start a session search.
 */
export function useStartSessionSearch() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: (data: SessionSearchRequest) => api.startSessionSearch(data, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
    },
  });
}

/**
 * Hook to connect to session search WebSocket and receive real-time updates.
 */
export function useSessionSearchWebSocket(monitorId: string | null) {
  const [messages, setMessages] = useState<SessionSearchMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  const connect = useCallback(() => {
    if (!monitorId || wsRef.current) return;

    const ws = api.connectSessionSearchWs(monitorId, (data) => {
      const msg = data as SessionSearchMessage;
      setMessages((prev) => [...prev, msg]);

      if (msg.type === 'started') {
        setStatus('running');
      } else if (msg.type === 'completed') {
        setStatus('completed');
        if (msg.result) {
          setResult(msg.result);
        }
        queryClient.invalidateQueries({ queryKey: ['bookings'] });
        queryClient.invalidateQueries({ queryKey: ['members'] });
      } else if (msg.type === 'error') {
        setStatus('error');
      }
    });

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
    };
    ws.onerror = () => {
      setIsConnected(false);
      setStatus('error');
    };

    wsRef.current = ws;
  }, [monitorId, queryClient]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendStop = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('stop');
    }
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setStatus('idle');
    setResult(null);
  }, []);

  return {
    messages,
    isConnected,
    status,
    result,
    connect,
    disconnect,
    sendStop,
    reset,
  };
}
