'use client';

import { useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';
import type { StartMonitorRequest } from '@/types';

interface MonitorMessage {
  type: 'status' | 'started' | 'completed' | 'error';
  level?: string;
  message?: string;
  results?: Record<number, unknown>;
  elapsed_seconds?: number;
}

export function useMonitor(monitorId?: string) {
  return useQuery({
    queryKey: ['monitor', monitorId],
    queryFn: () => api.getMonitorStatus(monitorId!),
    enabled: !!monitorId,
    refetchInterval: 5000, // Poll every 5 seconds
  });
}

export function useMonitors() {
  return useQuery({
    queryKey: ['monitors'],
    queryFn: () => api.listMonitors(),
  });
}

export function useStartMonitor() {
  const queryClient = useQueryClient();
  const sport = useAuthStore((state) => state.sport);

  return useMutation({
    mutationFn: (data: StartMonitorRequest) => api.startMonitor(data, sport),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
    },
  });
}

export function useStopMonitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (monitorId: string) => api.stopMonitor(monitorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
    },
  });
}

export function useMonitorWebSocket(monitorId: string | null) {
  const [messages, setMessages] = useState<MonitorMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'error'>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  const queryClient = useQueryClient();

  const connect = useCallback(() => {
    if (!monitorId || wsRef.current) return;

    const ws = api.connectMonitorWs(monitorId, (data) => {
      const msg = data as MonitorMessage;
      setMessages((prev) => [...prev, msg]);

      if (msg.type === 'started') {
        setStatus('running');
      } else if (msg.type === 'completed') {
        setStatus('completed');
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

  return {
    messages,
    isConnected,
    status,
    connect,
    disconnect,
    sendStop,
  };
}
