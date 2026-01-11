'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Square, RefreshCw, Clock, CheckCircle, XCircle, Radio, User, GraduationCap, Waves, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button, Badge } from '@/components/ui';
import { useActiveMonitors } from '@/hooks';
import { useMonitorStore, type MonitorInfo } from '@/lib/store';
import { formatLevel, formatWaveSide, formatDateBR } from '@/lib/utils';
import { useSessionOptions } from '@/hooks';

// Constants for form options
const LEVELS = [
  { value: 'Iniciante1', label: 'Iniciante 1' },
  { value: 'Iniciante2', label: 'Iniciante 2' },
  { value: 'Intermediario1', label: 'Intermediario 1' },
  { value: 'Intermediario2', label: 'Intermediario 2' },
  { value: 'Avançado1', label: 'Avancado 1' },
  { value: 'Avançado2', label: 'Avancado 2' },
];

const WAVE_SIDES = [
  { value: 'Lado_esquerdo', label: 'Esquerda' },
  { value: 'Lado_direito', label: 'Direita' },
];

const DURATIONS = [60, 120, 180, 240, 300, 360];

function formatElapsedTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}min ${secs}s`;
}

interface MonitorCardProps {
  monitor: MonitorInfo;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onStop: () => void;
  onUpdate: (data: { level?: string; wave_side?: string; target_hour?: string; duration_minutes?: number }) => void;
  isStoppingMonitor: boolean;
  isUpdatingMonitor: boolean;
  availableHours: string[];
}

function MonitorCard({
  monitor,
  isExpanded,
  onToggleExpand,
  onStop,
  onUpdate,
  isStoppingMonitor,
  isUpdatingMonitor,
  availableHours,
}: MonitorCardProps) {
  const [editLevel, setEditLevel] = useState(monitor.level);
  const [editWaveSide, setEditWaveSide] = useState(monitor.wave_side || '');
  const [editHour, setEditHour] = useState(monitor.target_hour || '');
  const [editDuration, setEditDuration] = useState(monitor.duration_minutes);

  const getStatusBadge = () => {
    switch (monitor.status) {
      case 'running':
        return <Badge variant="info">Buscando</Badge>;
      case 'completed':
        return <Badge variant="success">Concluido</Badge>;
      case 'error':
        return <Badge variant="danger">Erro</Badge>;
      case 'stopping':
        return <Badge variant="warning">Parando</Badge>;
      case 'pending':
        return <Badge variant="default">Pendente</Badge>;
      default:
        return <Badge variant="default">{monitor.status}</Badge>;
    }
  };

  const getStatusIcon = () => {
    switch (monitor.status) {
      case 'running':
        return <Radio className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const hasChanges =
    editLevel !== monitor.level ||
    editWaveSide !== (monitor.wave_side || '') ||
    editHour !== (monitor.target_hour || '') ||
    editDuration !== monitor.duration_minutes;

  const handleUpdate = () => {
    const updates: { level?: string; wave_side?: string; target_hour?: string; duration_minutes?: number } = {};
    if (editLevel !== monitor.level) updates.level = editLevel;
    if (editWaveSide !== (monitor.wave_side || '')) updates.wave_side = editWaveSide || undefined;
    if (editHour !== (monitor.target_hour || '')) updates.target_hour = editHour || undefined;
    if (editDuration !== monitor.duration_minutes) updates.duration_minutes = editDuration;
    onUpdate(updates);
  };

  return (
    <Card className={`${monitor.status === 'running' ? 'ring-2 ring-blue-200' : ''}`}>
      {/* Header - Always visible */}
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggleExpand}
      >
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900">{monitor.member_name}</span>
              {getStatusBadge()}
            </div>
            <div className="text-sm text-gray-500 flex items-center gap-2 mt-0.5">
              <span>{formatLevel(monitor.level)}</span>
              {monitor.wave_side && (
                <>
                  <span>•</span>
                  <span>{formatWaveSide(monitor.wave_side)}</span>
                </>
              )}
              <span>•</span>
              <span>{formatDateBR(monitor.target_date)}</span>
              {monitor.target_hour && (
                <>
                  <span>•</span>
                  <span>{monitor.target_hour}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {monitor.status === 'running' && (
            <span className="text-sm text-gray-500">
              {formatElapsedTime(monitor.elapsed_seconds)}
            </span>
          )}
          {isExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <CardContent className="border-t border-gray-100 pt-4 space-y-4">
          {/* Result if completed - only show if result has actual content */}
          {monitor.result && (monitor.result.success !== undefined || monitor.result.error) && (
            <div className={`p-3 rounded-lg ${
              monitor.result.success
                ? 'bg-green-50 border border-green-200'
                : 'bg-red-50 border border-red-200'
            }`}>
              {monitor.result.success ? (
                <>
                  <p className="text-sm font-medium text-green-800">Sessao Agendada!</p>
                  {monitor.result.voucher && (
                    <p className="text-xs text-green-700 mt-1">Voucher: {monitor.result.voucher}</p>
                  )}
                  {monitor.result.access_code && (
                    <p className="text-xs text-green-700">Codigo: {monitor.result.access_code}</p>
                  )}
                </>
              ) : (
                <>
                  <p className="text-sm font-medium text-red-800">Busca Finalizada</p>
                  {monitor.result.error && (
                    <p className="text-xs text-red-700 mt-1">{monitor.result.error}</p>
                  )}
                </>
              )}
            </div>
          )}

          {/* Edit form - only for running/pending monitors */}
          {(monitor.status === 'running' || monitor.status === 'pending') && (
            <div className="space-y-4">
              {/* Level */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  <GraduationCap className="h-4 w-4" />
                  Nivel
                </label>
                <select
                  value={editLevel}
                  onChange={(e) => setEditLevel(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  {LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>
                      {level.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Wave Side */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  <Waves className="h-4 w-4" />
                  Lado
                </label>
                <select
                  value={editWaveSide}
                  onChange={(e) => setEditWaveSide(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Ambos</option>
                  {WAVE_SIDES.map((side) => (
                    <option key={side.value} value={side.value}>
                      {side.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Hour */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  Horario
                </label>
                <select
                  value={editHour}
                  onChange={(e) => setEditHour(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">Qualquer</option>
                  {availableHours.map((hour) => (
                    <option key={hour} value={hour}>
                      {hour}
                    </option>
                  ))}
                </select>
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Duracao
                </label>
                <select
                  value={editDuration}
                  onChange={(e) => setEditDuration(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  {DURATIONS.map((d) => (
                    <option key={d} value={d}>
                      {d} minutos
                    </option>
                  ))}
                </select>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleUpdate}
                  disabled={!hasChanges || isUpdatingMonitor}
                  isLoading={isUpdatingMonitor}
                  className="flex-1"
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Atualizar
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={onStop}
                  disabled={isStoppingMonitor}
                  isLoading={isStoppingMonitor}
                  className="flex-1"
                >
                  <Square className="h-4 w-4 mr-1" />
                  Parar
                </Button>
              </div>
            </div>
          )}

          {/* Logs */}
          {monitor.messages.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Logs</p>
              <div className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-y-auto font-mono text-xs">
                {monitor.messages.slice(-20).map((msg, idx) => (
                  <div
                    key={idx}
                    className={`mb-1 ${
                      msg.level === 'error'
                        ? 'text-red-400'
                        : msg.level === 'warning'
                        ? 'text-yellow-400'
                        : msg.level === 'success'
                        ? 'text-green-400'
                        : 'text-gray-300'
                    }`}
                  >
                    {msg.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

export function MonitorList() {
  const { monitors, stopMonitor, updateMonitorConfig, isStoppingMonitor, isUpdatingMonitor } = useActiveMonitors();
  const { expandedMonitorId, setExpanded } = useMonitorStore();
  const { data: sessionOptions } = useSessionOptions();

  // Sort monitors: running first, then by started_at desc
  const sortedMonitors = [...monitors].sort((a, b) => {
    if (a.status === 'running' && b.status !== 'running') return -1;
    if (a.status !== 'running' && b.status === 'running') return 1;
    return (b.started_at || 0) - (a.started_at || 0);
  });

  if (sortedMonitors.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Radio className="h-5 w-5" />
          Monitors Ativos
          <Badge variant="default" className="ml-2">
            {sortedMonitors.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {sortedMonitors.map((monitor) => {
          const availableHours = monitor.level && sessionOptions?.hours_by_level
            ? sessionOptions.hours_by_level[monitor.level] || []
            : [];

          return (
            <MonitorCard
              key={monitor.monitor_id}
              monitor={monitor}
              isExpanded={expandedMonitorId === monitor.monitor_id}
              onToggleExpand={() =>
                setExpanded(expandedMonitorId === monitor.monitor_id ? null : monitor.monitor_id)
              }
              onStop={() => stopMonitor(monitor.monitor_id)}
              onUpdate={(data) => updateMonitorConfig(monitor.monitor_id, data)}
              isStoppingMonitor={isStoppingMonitor}
              isUpdatingMonitor={isUpdatingMonitor}
              availableHours={availableHours}
            />
          );
        })}
      </CardContent>
    </Card>
  );
}
