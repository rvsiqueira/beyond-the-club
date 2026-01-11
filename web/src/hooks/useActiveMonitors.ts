'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useMonitorStore, useToastStore, type MonitorInfo } from '@/lib/store';
import { useRouter } from 'next/navigation';

const POLL_INTERVAL = 10000; // 10 seconds

export function useActiveMonitors() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { monitors, syncFromServer, updateMonitor, removeMonitor } = useMonitorStore();
  const { addToast } = useToastStore();
  const previousMonitorsRef = useRef<Record<string, MonitorInfo>>({});
  const [hasCheckedInitial, setHasCheckedInitial] = useState(false);

  // Check if we have any active monitors to poll
  const hasActiveMonitors = Object.values(monitors).some(
    (m) => m.status === 'running' || m.status === 'pending' || m.status === 'stopping'
  );

  // Query for active monitors
  // Always enabled on first load to check for existing monitors, then only poll if there are active monitors
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['activeMonitors'],
    queryFn: () => api.getActiveMonitors(),
    refetchInterval: hasActiveMonitors ? POLL_INTERVAL : false,
    // Always run on mount to sync with server, then continue polling if there are active monitors
    enabled: !hasCheckedInitial || hasActiveMonitors,
  });

  // Mark initial check as done after first successful fetch
  useEffect(() => {
    if (data && !hasCheckedInitial) {
      setHasCheckedInitial(true);
    }
  }, [data, hasCheckedInitial]);

  // Sync server data with store and check for completed monitors
  useEffect(() => {
    if (data?.monitors) {
      const serverMonitors = data.monitors as MonitorInfo[];
      syncFromServer(serverMonitors);

      // Check for monitors that just completed
      for (const monitor of serverMonitors) {
        const prevMonitor = previousMonitorsRef.current[monitor.monitor_id];
        if (
          prevMonitor &&
          prevMonitor.status === 'running' &&
          (monitor.status === 'completed' || monitor.status === 'error')
        ) {
          // Monitor just finished - show toast
          if (monitor.result?.success) {
            addToast({
              type: 'success',
              title: 'Sessão Agendada!',
              message: `${monitor.member_name}: ${monitor.level} - ${monitor.target_date}`,
              duration: 15000,
              action: {
                label: 'Ver Agendamentos',
                onClick: () => router.push('/bookings'),
              },
            });
          } else if (monitor.status === 'error' || monitor.result?.error) {
            addToast({
              type: 'error',
              title: 'Monitor Falhou',
              message: monitor.result?.error || 'Erro desconhecido',
              duration: 10000,
            });
          }
        }
      }

      // Update previous monitors ref
      previousMonitorsRef.current = serverMonitors.reduce(
        (acc, m) => ({ ...acc, [m.monitor_id]: m }),
        {}
      );
    }
  }, [data, syncFromServer, addToast, router]);

  // Stop monitor mutation
  const stopMutation = useMutation({
    mutationFn: (monitorId: string) => api.stopMonitor(monitorId),
    onSuccess: (_, monitorId) => {
      updateMonitor(monitorId, { status: 'stopping' });
      refetch();
    },
    onError: (error) => {
      addToast({
        type: 'error',
        title: 'Erro ao parar monitor',
        message: error instanceof Error ? error.message : 'Erro desconhecido',
      });
    },
  });

  // Update monitor mutation
  const updateMutation = useMutation({
    mutationFn: ({
      monitorId,
      data,
    }: {
      monitorId: string;
      data: { level?: string; wave_side?: string; target_hour?: string; duration_minutes?: number };
    }) => api.updateMonitor(monitorId, data),
    onSuccess: (result, { monitorId }) => {
      addToast({
        type: 'success',
        title: 'Monitor Atualizado',
        message: result.message,
      });
      if (result.restarted) {
        updateMonitor(monitorId, { status: 'pending' });
      }
      refetch();
    },
    onError: (error) => {
      addToast({
        type: 'error',
        title: 'Erro ao atualizar monitor',
        message: error instanceof Error ? error.message : 'Erro desconhecido',
      });
    },
  });

  const stopMonitor = useCallback(
    (monitorId: string) => {
      stopMutation.mutate(monitorId);
    },
    [stopMutation]
  );

  const updateMonitorConfig = useCallback(
    (
      monitorId: string,
      data: { level?: string; wave_side?: string; target_hour?: string; duration_minutes?: number }
    ) => {
      updateMutation.mutate({ monitorId, data });
    },
    [updateMutation]
  );

  return {
    monitors: Object.values(monitors),
    isLoading,
    error,
    refetch,
    stopMonitor,
    updateMonitorConfig,
    isStoppingMonitor: stopMutation.isPending,
    isUpdatingMonitor: updateMutation.isPending,
  };
}
